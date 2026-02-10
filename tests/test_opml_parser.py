"""Tests for OPML parser."""

import os
import tempfile

from hn_intel.opml_parser import parse_opml

SAMPLE_OPML = """\
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Test</title></head>
  <body>
    <outline text="Blogs" title="Blogs">
      <outline type="rss" text="Example Blog" title="Example Blog"
               xmlUrl="https://example.com/feed.xml"
               htmlUrl="https://example.com"/>
      <outline type="rss" text="Another Blog" title="Another Blog"
               xmlUrl="https://another.com/rss"
               htmlUrl="https://another.com"/>
      <outline text="Not RSS" title="Folder"/>
    </outline>
  </body>
</opml>
"""


def test_parse_opml_returns_feeds():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".opml", delete=False) as f:
        f.write(SAMPLE_OPML)
        f.flush()
        path = f.name

    try:
        feeds = parse_opml(path)
        assert len(feeds) == 2
        assert feeds[0]["name"] == "Example Blog"
        assert feeds[0]["feed_url"] == "https://example.com/feed.xml"
        assert feeds[0]["site_url"] == "https://example.com"
        assert feeds[1]["name"] == "Another Blog"
    finally:
        os.unlink(path)


def test_parse_opml_real_file():
    opml_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "hn-blogs.opml"
    )
    if not os.path.exists(opml_path):
        return
    feeds = parse_opml(opml_path)
    assert len(feeds) == 92
    names = [f["name"] for f in feeds]
    assert "simonwillison.net" in names


def test_parse_opml_skips_non_rss():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".opml", delete=False) as f:
        f.write(SAMPLE_OPML)
        f.flush()
        path = f.name

    try:
        feeds = parse_opml(path)
        feed_names = [f["name"] for f in feeds]
        assert "Not RSS" not in feed_names
    finally:
        os.unlink(path)
