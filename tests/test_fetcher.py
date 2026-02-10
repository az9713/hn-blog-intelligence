"""Tests for feed fetcher."""

import os
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

from hn_intel.db import init_db, get_blogs, get_all_posts
from hn_intel.fetcher import fetch_all_feeds, _parse_published


def _temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn, path


def _temp_opml(feeds):
    """Create a temp OPML file with given feed dicts."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0"><head><title>Test</title></head><body>',
        '<outline text="Blogs" title="Blogs">',
    ]
    for f in feeds:
        lines.append(
            f'<outline type="rss" text="{f["name"]}" title="{f["name"]}" '
            f'xmlUrl="{f["feed_url"]}" htmlUrl="{f["site_url"]}"/>'
        )
    lines.append("</outline></body></opml>")

    fd, path = tempfile.mkstemp(suffix=".opml")
    os.close(fd)
    with open(path, "w") as fh:
        fh.write("\n".join(lines))
    return path


FAKE_RSS = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Blog</title>
    <item>
      <title>Hello World</title>
      <link>https://test.com/hello</link>
      <description>A test post</description>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <author>Tester</author>
    </item>
    <item>
      <title>Second Post</title>
      <link>https://test.com/second</link>
      <description>Another post</description>
    </item>
  </channel>
</rss>
"""


def test_fetch_all_feeds_success():
    conn, db_path = _temp_db()
    opml_path = _temp_opml([
        {"name": "Test Blog", "feed_url": "https://test.com/feed", "site_url": "https://test.com"},
    ])

    try:
        init_db(conn)

        mock_resp = MagicMock()
        mock_resp.content = FAKE_RSS
        mock_resp.raise_for_status = MagicMock()

        with patch("hn_intel.fetcher.requests.get", return_value=mock_resp):
            with patch("hn_intel.fetcher.time.sleep"):
                summary = fetch_all_feeds(conn, opml_path=opml_path, timeout=10, delay=0)

        assert summary["feeds_ok"] == 1
        assert summary["feeds_err"] == 0
        assert summary["new_posts"] == 2

        posts = get_all_posts(conn)
        assert len(posts) == 2

        blogs = get_blogs(conn)
        assert blogs[0]["fetch_status"] == "ok"
    finally:
        conn.close()
        os.unlink(db_path)
        os.unlink(opml_path)


def test_fetch_all_feeds_error_handling():
    conn, db_path = _temp_db()
    opml_path = _temp_opml([
        {"name": "Bad Blog", "feed_url": "https://bad.com/feed", "site_url": "https://bad.com"},
    ])

    try:
        init_db(conn)

        with patch("hn_intel.fetcher.requests.get", side_effect=Exception("timeout")):
            with patch("hn_intel.fetcher.time.sleep"):
                summary = fetch_all_feeds(conn, opml_path=opml_path, timeout=10, delay=0)

        assert summary["feeds_ok"] == 0
        assert summary["feeds_err"] == 1

        blogs = get_blogs(conn)
        assert "timeout" in blogs[0]["fetch_status"]
    finally:
        conn.close()
        os.unlink(db_path)
        os.unlink(opml_path)


def test_parse_published():
    import time
    entry_with_date = {"published_parsed": time.strptime("2024-01-15", "%Y-%m-%d")}
    result = _parse_published(entry_with_date)
    assert result.startswith("2024-01-15")

    entry_without = {}
    assert _parse_published(entry_without) == ""


def test_fetch_dedup():
    """Fetching the same feed twice should not duplicate posts."""
    conn, db_path = _temp_db()
    opml_path = _temp_opml([
        {"name": "Test Blog", "feed_url": "https://test.com/feed", "site_url": "https://test.com"},
    ])

    try:
        init_db(conn)

        mock_resp = MagicMock()
        mock_resp.content = FAKE_RSS
        mock_resp.raise_for_status = MagicMock()

        with patch("hn_intel.fetcher.requests.get", return_value=mock_resp):
            with patch("hn_intel.fetcher.time.sleep"):
                fetch_all_feeds(conn, opml_path=opml_path, timeout=10, delay=0)
                summary = fetch_all_feeds(conn, opml_path=opml_path, timeout=10, delay=0)

        assert summary["new_posts"] == 0
        assert summary["skipped"] == 2
        assert len(get_all_posts(conn)) == 2
    finally:
        conn.close()
        os.unlink(db_path)
        os.unlink(opml_path)
