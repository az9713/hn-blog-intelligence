"""Tests for database layer."""

import sqlite3
import tempfile
import os

from hn_intel.db import (
    get_connection,
    init_db,
    upsert_blogs,
    insert_post,
    get_all_posts,
    get_blog_domains,
    get_blogs,
)


def _temp_db():
    """Create a temporary database connection."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn, path


def test_init_db_creates_tables():
    conn, path = _temp_db()
    try:
        init_db(conn)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "blogs" in table_names
        assert "posts" in table_names
        assert "citations" in table_names
    finally:
        conn.close()
        os.unlink(path)


def test_upsert_blogs():
    conn, path = _temp_db()
    try:
        init_db(conn)
        blogs = [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
            {"name": "Blog B", "feed_url": "https://b.com/feed", "site_url": "https://b.com"},
        ]
        upsert_blogs(conn, blogs)
        rows = get_blogs(conn)
        assert len(rows) == 2

        # Inserting again should not duplicate
        upsert_blogs(conn, blogs)
        rows = get_blogs(conn)
        assert len(rows) == 2
    finally:
        conn.close()
        os.unlink(path)


def test_insert_post_dedup():
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
        ])
        blog_id = conn.execute("SELECT id FROM blogs").fetchone()["id"]

        entry = {
            "title": "Post 1",
            "description": "Desc",
            "url": "https://a.com/post-1",
            "published": "2024-01-01",
            "author": "Author",
        }
        assert insert_post(conn, blog_id, entry) is True
        assert insert_post(conn, blog_id, entry) is False
    finally:
        conn.close()
        os.unlink(path)


def test_get_all_posts():
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
        ])
        blog_id = conn.execute("SELECT id FROM blogs").fetchone()["id"]

        insert_post(conn, blog_id, {
            "title": "Post 1",
            "description": "Desc",
            "url": "https://a.com/post-1",
            "published": "2024-01-01",
            "author": "Author",
        })

        posts = get_all_posts(conn)
        assert len(posts) == 1
        assert posts[0]["blog_name"] == "Blog A"
        assert posts[0]["title"] == "Post 1"
    finally:
        conn.close()
        os.unlink(path)


def test_get_blog_domains():
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
            {"name": "Blog B", "feed_url": "https://b.com/feed", "site_url": "https://www.b.com"},
        ])
        domains = get_blog_domains(conn)
        assert "a.com" in domains
        assert "b.com" in domains  # www. stripped
    finally:
        conn.close()
        os.unlink(path)


def test_get_connection():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "subdir", "test.db")
        conn = get_connection(db_path)
        try:
            assert os.path.exists(db_path)
            # Verify row_factory is set
            init_db(conn)
            upsert_blogs(conn, [
                {"name": "X", "feed_url": "https://x.com/feed", "site_url": "https://x.com"},
            ])
            row = conn.execute("SELECT * FROM blogs").fetchone()
            assert row["name"] == "X"
        finally:
            conn.close()
