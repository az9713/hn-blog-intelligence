"""SQLite database layer for HN Blog Intelligence."""

import os
import sqlite3
from urllib.parse import urlparse


def get_connection(db_path="data/hn_intel.db"):
    """Open a SQLite connection, ensuring the parent directory exists.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row.
    """
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn):
    """Create tables and indexes if they don't exist.

    Args:
        conn: sqlite3.Connection instance.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS blogs (
            id INTEGER PRIMARY KEY,
            name TEXT,
            feed_url TEXT UNIQUE,
            site_url TEXT,
            last_fetched TEXT,
            fetch_status TEXT
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            blog_id INTEGER REFERENCES blogs(id),
            title TEXT,
            description TEXT,
            url TEXT UNIQUE,
            published TEXT,
            author TEXT
        );

        CREATE TABLE IF NOT EXISTS citations (
            id INTEGER PRIMARY KEY,
            source_post_id INTEGER REFERENCES posts(id),
            source_blog_id INTEGER REFERENCES blogs(id),
            target_blog_id INTEGER REFERENCES blogs(id),
            target_url TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_posts_blog_id ON posts(blog_id);
        CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published);
        CREATE INDEX IF NOT EXISTS idx_citations_source_blog_id ON citations(source_blog_id);
        CREATE INDEX IF NOT EXISTS idx_citations_target_blog_id ON citations(target_blog_id);
    """)


def upsert_blogs(conn, blogs):
    """Insert blogs, ignoring duplicates by feed_url.

    Args:
        conn: sqlite3.Connection instance.
        blogs: List of dicts with keys: name, feed_url, site_url.
    """
    conn.executemany(
        "INSERT OR IGNORE INTO blogs (name, feed_url, site_url) VALUES (?, ?, ?)",
        [(b["name"], b["feed_url"], b["site_url"]) for b in blogs],
    )
    conn.commit()


def insert_post(conn, blog_id, entry):
    """Insert a single post, returning False if URL already exists.

    Args:
        conn: sqlite3.Connection instance.
        blog_id: ID of the blog this post belongs to.
        entry: Dict with keys: title, description, url, published, author.

    Returns:
        True if inserted, False if duplicate URL.
    """
    try:
        conn.execute(
            "INSERT INTO posts (blog_id, title, description, url, published, author) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                blog_id,
                entry.get("title", ""),
                entry.get("description", ""),
                entry["url"],
                entry.get("published", ""),
                entry.get("author", ""),
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_all_posts(conn):
    """Return all posts with the blog name joined.

    Args:
        conn: sqlite3.Connection instance.

    Returns:
        List of sqlite3.Row objects.
    """
    return conn.execute(
        "SELECT p.*, b.name AS blog_name "
        "FROM posts p JOIN blogs b ON p.blog_id = b.id"
    ).fetchall()


def get_blog_domains(conn):
    """Build a mapping of domain -> blog_id from site_url.

    Args:
        conn: sqlite3.Connection instance.

    Returns:
        Dict mapping domain strings to blog IDs.
    """
    rows = conn.execute("SELECT id, site_url FROM blogs").fetchall()
    domains = {}
    for row in rows:
        site_url = row["site_url"]
        if site_url:
            domain = urlparse(site_url).netloc
            if domain.startswith("www."):
                domain = domain[4:]
            if domain:
                domains[domain] = row["id"]
    return domains


def get_blogs(conn):
    """Return all blogs.

    Args:
        conn: sqlite3.Connection instance.

    Returns:
        List of sqlite3.Row objects.
    """
    return conn.execute("SELECT * FROM blogs").fetchall()
