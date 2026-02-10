"""Tests for network analysis module."""

import os
import sqlite3
import tempfile

from hn_intel.db import init_db, upsert_blogs, insert_post
from hn_intel.network import (
    extract_citations,
    build_citation_graph,
    compute_centrality,
    _normalize_domain,
    _domain_from_url,
)


def _temp_db():
    """Create a temporary database connection."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn, path


def _setup_blogs_and_posts(conn):
    """Set up test blogs and posts with cross-citations.

    Creates three blogs:
      - Blog A (a.com) with a post linking to Blog B and Blog C
      - Blog B (b.com) with a post linking to Blog A
      - Blog C (c.com) with a post with no outgoing citations

    Returns:
        Tuple of (blog_a_id, blog_b_id, blog_c_id).
    """
    init_db(conn)
    upsert_blogs(conn, [
        {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
        {"name": "Blog B", "feed_url": "https://b.com/feed", "site_url": "https://b.com"},
        {"name": "Blog C", "feed_url": "https://c.com/feed", "site_url": "https://c.com"},
    ])

    blog_a = conn.execute("SELECT id FROM blogs WHERE name='Blog A'").fetchone()["id"]
    blog_b = conn.execute("SELECT id FROM blogs WHERE name='Blog B'").fetchone()["id"]
    blog_c = conn.execute("SELECT id FROM blogs WHERE name='Blog C'").fetchone()["id"]

    # Blog A post links to Blog B and Blog C
    insert_post(conn, blog_a, {
        "title": "Post from A",
        "description": (
            '<p>Check out <a href="https://b.com/article">this post</a> '
            'and also <a href="https://c.com/other">this one</a>.</p>'
        ),
        "url": "https://a.com/post-1",
        "published": "2024-01-01",
        "author": "Author A",
    })

    # Blog B post links to Blog A
    insert_post(conn, blog_b, {
        "title": "Post from B",
        "description": '<p>See <a href="https://a.com/post-1">Blog A</a>.</p>',
        "url": "https://b.com/post-1",
        "published": "2024-01-02",
        "author": "Author B",
    })

    # Blog C post with no outgoing links (or only self-link)
    insert_post(conn, blog_c, {
        "title": "Post from C",
        "description": '<p>My own <a href="https://c.com/about">about page</a>.</p>',
        "url": "https://c.com/post-1",
        "published": "2024-01-03",
        "author": "Author C",
    })

    return blog_a, blog_b, blog_c


def test_normalize_domain():
    assert _normalize_domain("www.example.com") == "example.com"
    assert _normalize_domain("Example.COM") == "example.com"
    assert _normalize_domain("alice.blogspot.com") == "alice.blogspot.com"
    assert _normalize_domain("WWW.Alice.Blogspot.com") == "alice.blogspot.com"


def test_domain_from_url():
    assert _domain_from_url("https://www.example.com/path") == "example.com"
    assert _domain_from_url("http://blog.example.com/post") == "blog.example.com"
    assert _domain_from_url("") == ""
    assert _domain_from_url("not-a-url") == ""


def test_extract_citations():
    conn, path = _temp_db()
    try:
        blog_a, blog_b, blog_c = _setup_blogs_and_posts(conn)
        count = extract_citations(conn)

        # Blog A -> Blog B, Blog A -> Blog C, Blog B -> Blog A = 3
        assert count == 3

        citations = conn.execute("SELECT * FROM citations").fetchall()
        assert len(citations) == 3

        # Check Blog A -> Blog B citation
        a_to_b = conn.execute(
            "SELECT * FROM citations WHERE source_blog_id=? AND target_blog_id=?",
            (blog_a, blog_b),
        ).fetchall()
        assert len(a_to_b) == 1
        assert "b.com" in a_to_b[0]["target_url"]

        # Check Blog A -> Blog C citation
        a_to_c = conn.execute(
            "SELECT * FROM citations WHERE source_blog_id=? AND target_blog_id=?",
            (blog_a, blog_c),
        ).fetchall()
        assert len(a_to_c) == 1

        # Check Blog B -> Blog A citation
        b_to_a = conn.execute(
            "SELECT * FROM citations WHERE source_blog_id=? AND target_blog_id=?",
            (blog_b, blog_a),
        ).fetchall()
        assert len(b_to_a) == 1

        # Check no self-citation for Blog C
        c_to_c = conn.execute(
            "SELECT * FROM citations WHERE source_blog_id=? AND target_blog_id=?",
            (blog_c, blog_c),
        ).fetchall()
        assert len(c_to_c) == 0
    finally:
        conn.close()
        os.unlink(path)


def test_extract_citations_skips_self():
    """Self-citations should not be recorded."""
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog X", "feed_url": "https://x.com/feed", "site_url": "https://x.com"},
        ])
        blog_x = conn.execute("SELECT id FROM blogs").fetchone()["id"]
        insert_post(conn, blog_x, {
            "title": "Self-referential",
            "description": '<a href="https://x.com/other-post">link</a>',
            "url": "https://x.com/post-1",
            "published": "2024-01-01",
            "author": "X",
        })

        count = extract_citations(conn)
        assert count == 0
    finally:
        conn.close()
        os.unlink(path)


def test_extract_citations_www_normalization():
    """Links with www. prefix should match blogs without www."""
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
            {"name": "Blog B", "feed_url": "https://b.com/feed", "site_url": "https://b.com"},
        ])
        blog_a = conn.execute("SELECT id FROM blogs WHERE name='Blog A'").fetchone()["id"]

        insert_post(conn, blog_a, {
            "title": "WWW link",
            "description": '<a href="https://www.b.com/article">link</a>',
            "url": "https://a.com/post-www",
            "published": "2024-01-01",
            "author": "A",
        })

        count = extract_citations(conn)
        assert count == 1

        citation = conn.execute("SELECT * FROM citations").fetchone()
        assert citation["source_blog_id"] == blog_a
    finally:
        conn.close()
        os.unlink(path)


def test_extract_citations_shared_platform():
    """Shared platform subdomains should be distinguished."""
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {
                "name": "Alice Blog",
                "feed_url": "https://alice.substack.com/feed",
                "site_url": "https://alice.substack.com",
            },
            {
                "name": "Bob Blog",
                "feed_url": "https://bob.substack.com/feed",
                "site_url": "https://bob.substack.com",
            },
        ])
        alice_id = conn.execute("SELECT id FROM blogs WHERE name='Alice Blog'").fetchone()["id"]
        bob_id = conn.execute("SELECT id FROM blogs WHERE name='Bob Blog'").fetchone()["id"]

        # Alice links to Bob
        insert_post(conn, alice_id, {
            "title": "Cross-substack",
            "description": '<a href="https://bob.substack.com/p/post1">Bob post</a>',
            "url": "https://alice.substack.com/p/my-post",
            "published": "2024-01-01",
            "author": "Alice",
        })

        count = extract_citations(conn)
        assert count == 1

        citation = conn.execute("SELECT * FROM citations").fetchone()
        assert citation["source_blog_id"] == alice_id
        assert citation["target_blog_id"] == bob_id
    finally:
        conn.close()
        os.unlink(path)


def test_build_citation_graph():
    conn, path = _temp_db()
    try:
        blog_a, blog_b, blog_c = _setup_blogs_and_posts(conn)
        extract_citations(conn)
        graph = build_citation_graph(conn)

        # 3 blogs = 3 nodes
        assert len(graph.nodes()) == 3

        # Blog A -> Blog B, Blog A -> Blog C, Blog B -> Blog A = 3 edges
        assert len(graph.edges()) == 3

        # Check node names
        assert graph.nodes[blog_a]["name"] == "Blog A"
        assert graph.nodes[blog_b]["name"] == "Blog B"
        assert graph.nodes[blog_c]["name"] == "Blog C"

        # Check edge weights
        assert graph[blog_a][blog_b]["weight"] == 1
        assert graph[blog_a][blog_c]["weight"] == 1
        assert graph[blog_b][blog_a]["weight"] == 1

        # Blog C has no outgoing edges
        assert graph.out_degree(blog_c) == 0
        # Blog C has 1 incoming edge (from Blog A)
        assert graph.in_degree(blog_c) == 1
    finally:
        conn.close()
        os.unlink(path)


def test_compute_centrality():
    conn, path = _temp_db()
    try:
        _setup_blogs_and_posts(conn)
        extract_citations(conn)
        graph = build_citation_graph(conn)
        centrality = compute_centrality(graph)

        assert "Blog A" in centrality
        assert "Blog B" in centrality
        assert "Blog C" in centrality

        # Blog A: out_degree=2, in_degree=1
        assert centrality["Blog A"]["out_degree"] == 2
        assert centrality["Blog A"]["in_degree"] == 1

        # Blog B: out_degree=1, in_degree=1
        assert centrality["Blog B"]["out_degree"] == 1
        assert centrality["Blog B"]["in_degree"] == 1

        # Blog C: out_degree=0, in_degree=1
        assert centrality["Blog C"]["out_degree"] == 0
        assert centrality["Blog C"]["in_degree"] == 1

        # PageRank values should sum to ~1.0
        total_pr = sum(c["pagerank"] for c in centrality.values())
        assert abs(total_pr - 1.0) < 0.01

        # All metrics should be non-negative
        for metrics in centrality.values():
            assert metrics["pagerank"] >= 0
            assert metrics["betweenness"] >= 0
            assert metrics["in_degree"] >= 0
            assert metrics["out_degree"] >= 0
    finally:
        conn.close()
        os.unlink(path)


def test_compute_centrality_empty_graph():
    """compute_centrality should handle an empty graph."""
    import networkx as nx
    graph = nx.DiGraph()
    result = compute_centrality(graph)
    assert result == {}


def test_extract_citations_single_quotes():
    """href with single quotes should also be matched."""
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
            {"name": "Blog B", "feed_url": "https://b.com/feed", "site_url": "https://b.com"},
        ])
        blog_a = conn.execute("SELECT id FROM blogs WHERE name='Blog A'").fetchone()["id"]

        insert_post(conn, blog_a, {
            "title": "Single quote link",
            "description": "<a href='https://b.com/article'>link</a>",
            "url": "https://a.com/post-sq",
            "published": "2024-01-01",
            "author": "A",
        })

        count = extract_citations(conn)
        assert count == 1
    finally:
        conn.close()
        os.unlink(path)


def test_extract_citations_no_description():
    """Posts with empty or None descriptions should not cause errors."""
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
        ])
        blog_a = conn.execute("SELECT id FROM blogs").fetchone()["id"]

        insert_post(conn, blog_a, {
            "title": "Empty desc",
            "description": "",
            "url": "https://a.com/post-empty",
            "published": "2024-01-01",
            "author": "A",
        })
        insert_post(conn, blog_a, {
            "title": "No desc",
            "url": "https://a.com/post-none",
            "published": "2024-01-01",
            "author": "A",
        })

        count = extract_citations(conn)
        assert count == 0
    finally:
        conn.close()
        os.unlink(path)
