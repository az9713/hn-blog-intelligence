"""Fetch RSS feeds and store posts in the database."""

import time
from datetime import datetime, timezone

import feedparser
import requests
from tqdm import tqdm

from hn_intel.db import init_db, insert_post, upsert_blogs
from hn_intel.opml_parser import parse_opml


def _parse_published(entry):
    """Extract a published date string from a feed entry.

    Args:
        entry: A feedparser entry dict.

    Returns:
        ISO-format date string, or empty string if unavailable.
    """
    parsed = entry.get("published_parsed")
    if parsed:
        try:
            return datetime(*parsed[:6]).isoformat()
        except Exception:
            return ""
    return ""


def fetch_all_feeds(conn, opml_path="docs/hn-blogs.opml", timeout=30, delay=0.5):
    """Fetch all feeds from an OPML file and insert posts into the database.

    Args:
        conn: sqlite3.Connection instance (already initialized).
        opml_path: Path to the OPML file.
        timeout: Request timeout in seconds per feed.
        delay: Delay in seconds between feed requests.

    Returns:
        Dict with summary stats: feeds_ok, feeds_err, new_posts, skipped.
    """
    blogs = parse_opml(opml_path)
    init_db(conn)
    upsert_blogs(conn, blogs)

    # Build feed_url -> blog row mapping
    rows = conn.execute("SELECT id, feed_url FROM blogs").fetchall()
    url_to_id = {row["feed_url"]: row["id"] for row in rows}

    summary = {"feeds_ok": 0, "feeds_err": 0, "new_posts": 0, "skipped": 0}

    for blog in tqdm(blogs, desc="Fetching feeds"):
        feed_url = blog["feed_url"]
        blog_id = url_to_id.get(feed_url)
        if blog_id is None:
            continue

        now = datetime.now(timezone.utc).isoformat()
        try:
            resp = requests.get(feed_url, timeout=timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            for entry in feed.entries:
                link = entry.get("link", "")
                if not link:
                    continue

                post = {
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", entry.get("description", "")),
                    "url": link,
                    "published": _parse_published(entry),
                    "author": entry.get("author", ""),
                }
                if insert_post(conn, blog_id, post):
                    summary["new_posts"] += 1
                else:
                    summary["skipped"] += 1

            conn.execute(
                "UPDATE blogs SET last_fetched = ?, fetch_status = ? WHERE id = ?",
                (now, "ok", blog_id),
            )
            conn.commit()
            summary["feeds_ok"] += 1

        except Exception as exc:
            conn.execute(
                "UPDATE blogs SET last_fetched = ?, fetch_status = ? WHERE id = ?",
                (now, str(exc)[:200], blog_id),
            )
            conn.commit()
            summary["feeds_err"] += 1

        time.sleep(delay)

    return summary
