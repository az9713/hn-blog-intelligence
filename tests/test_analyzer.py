"""Tests for the trend analyzer module."""

import sqlite3

from hn_intel.db import init_db, upsert_blogs, insert_post
from hn_intel.analyzer import (
    strip_html,
    extract_keywords,
    compute_trends,
    detect_emerging_topics,
    find_leading_blogs,
)


def _mem_db():
    """Create an in-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)
    return conn


def _seed_blogs(conn, blogs=None):
    """Insert default test blogs and return their IDs."""
    if blogs is None:
        blogs = [
            {"name": "Alpha Blog", "feed_url": "https://alpha.com/feed", "site_url": "https://alpha.com"},
            {"name": "Beta Blog", "feed_url": "https://beta.com/feed", "site_url": "https://beta.com"},
        ]
    upsert_blogs(conn, blogs)
    rows = conn.execute("SELECT id, name FROM blogs ORDER BY id").fetchall()
    return {row["name"]: row["id"] for row in rows}


def _seed_posts(conn):
    """Seed a realistic set of posts for trend analysis.

    Returns dict mapping blog name to blog_id.
    """
    ids = _seed_blogs(conn)

    # Alpha Blog posts about machine learning (earlier)
    posts_alpha = [
        {"title": "Introduction to machine learning algorithms",
         "description": "<p>A deep dive into <b>machine learning</b> algorithms and their applications.</p>",
         "url": "https://alpha.com/ml-intro", "published": "2024-01-15", "author": "Alice"},
        {"title": "Python machine learning best practices",
         "description": "<p>Best practices for building machine learning pipelines in Python.</p>",
         "url": "https://alpha.com/ml-best", "published": "2024-01-20", "author": "Alice"},
        {"title": "Neural networks explained",
         "description": "<p>Understanding neural networks and deep learning fundamentals.</p>",
         "url": "https://alpha.com/nn", "published": "2024-02-10", "author": "Alice"},
        {"title": "Data engineering with Rust",
         "description": "<p>Building high-performance data pipelines using Rust programming language.</p>",
         "url": "https://alpha.com/rust-data", "published": "2024-03-05", "author": "Alice"},
        {"title": "Kubernetes deployment strategies",
         "description": "<p>Advanced kubernetes deployment patterns for production workloads.</p>",
         "url": "https://alpha.com/k8s", "published": "2024-04-10", "author": "Alice"},
        {"title": "WebAssembly performance benchmarks",
         "description": "<p>Comparing WebAssembly performance across browsers and runtimes.</p>",
         "url": "https://alpha.com/wasm", "published": "2024-05-01", "author": "Alice"},
    ]

    # Beta Blog posts about machine learning (later) and other topics
    posts_beta = [
        {"title": "Getting started with databases",
         "description": "<p>An overview of modern database technologies and SQL basics.</p>",
         "url": "https://beta.com/db-intro", "published": "2024-01-25", "author": "Bob"},
        {"title": "Machine learning in production",
         "description": "<p>Deploying machine learning models to production environments.</p>",
         "url": "https://beta.com/ml-prod", "published": "2024-02-15", "author": "Bob"},
        {"title": "Rust for systems programming",
         "description": "<p>Why Rust is becoming the language of choice for systems programming.</p>",
         "url": "https://beta.com/rust-sys", "published": "2024-03-10", "author": "Bob"},
        {"title": "Advanced Kubernetes monitoring",
         "description": "<p>Setting up comprehensive kubernetes monitoring with Prometheus.</p>",
         "url": "https://beta.com/k8s-mon", "published": "2024-04-15", "author": "Bob"},
        {"title": "WebAssembly revolution in cloud computing",
         "description": "<p>How WebAssembly is transforming cloud computing workloads.</p>",
         "url": "https://beta.com/wasm-cloud", "published": "2024-05-10", "author": "Bob"},
        {"title": "WebAssembly serverless functions",
         "description": "<p>Building serverless functions with WebAssembly for edge computing.</p>",
         "url": "https://beta.com/wasm-serverless", "published": "2024-05-20", "author": "Bob"},
    ]

    for entry in posts_alpha:
        insert_post(conn, ids["Alpha Blog"], entry)
    for entry in posts_beta:
        insert_post(conn, ids["Beta Blog"], entry)

    return ids


# ── strip_html tests ──


def test_strip_html_basic():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello  world"


def test_strip_html_none():
    assert strip_html(None) == ""


def test_strip_html_empty():
    assert strip_html("") == ""


def test_strip_html_no_tags():
    assert strip_html("plain text") == "plain text"


# ── extract_keywords tests ──


def test_extract_keywords_empty_db():
    conn = _mem_db()
    vectorizer, matrix, post_ids = extract_keywords(conn)
    assert vectorizer is None
    assert matrix is None
    assert post_ids == []
    conn.close()


def test_extract_keywords_returns_components():
    conn = _mem_db()
    _seed_posts(conn)
    vectorizer, matrix, post_ids = extract_keywords(conn)

    assert vectorizer is not None
    assert matrix is not None
    assert len(post_ids) == 12
    # Matrix rows should match post count
    assert matrix.shape[0] == 12
    # Features should not exceed max_features
    assert matrix.shape[1] <= 500
    conn.close()


def test_extract_keywords_feature_names():
    conn = _mem_db()
    _seed_posts(conn)
    vectorizer, matrix, post_ids = extract_keywords(conn)
    feature_names = vectorizer.get_feature_names_out()
    # Should contain keywords from our posts
    feature_list = list(feature_names)
    assert len(feature_list) > 0
    conn.close()


# ── compute_trends tests ──


def test_compute_trends_empty_db():
    conn = _mem_db()
    trends = compute_trends(conn)
    assert trends == {}
    conn.close()


def test_compute_trends_returns_periods():
    conn = _mem_db()
    _seed_posts(conn)
    trends = compute_trends(conn, period="month")

    # We have posts from Jan-May 2024
    assert len(trends) > 0
    for key in trends:
        assert key.startswith("2024-")
    conn.close()


def test_compute_trends_values_are_normalized():
    conn = _mem_db()
    _seed_posts(conn)
    trends = compute_trends(conn, period="month")

    for period_key, scores in trends.items():
        for keyword, score in scores.items():
            # Normalized TF-IDF scores should be non-negative
            assert score >= 0
            # Individual normalized scores should be <= 1.0
            assert score <= 1.0
    conn.close()


def test_compute_trends_week_period():
    conn = _mem_db()
    _seed_posts(conn)
    trends = compute_trends(conn, period="week")

    # Week keys should have W format
    assert len(trends) > 0
    for key in trends:
        assert "-W" in key
    conn.close()


# ── detect_emerging_topics tests ──


def test_detect_emerging_topics_empty():
    result = detect_emerging_topics({})
    assert result == []


def test_detect_emerging_topics_insufficient_periods():
    trends = {
        "2024-01": {"python": 0.5},
        "2024-02": {"python": 0.6},
    }
    # Default window=3 means we need at least 4 periods
    result = detect_emerging_topics(trends, window=3)
    assert result == []


def test_detect_emerging_topics_detects_acceleration():
    # Simulate a keyword that spikes in recent periods
    trends = {
        "2024-01": {"stable": 0.1, "rising": 0.01},
        "2024-02": {"stable": 0.1, "rising": 0.01},
        "2024-03": {"stable": 0.1, "rising": 0.01},
        "2024-04": {"stable": 0.1, "rising": 0.05},
        "2024-05": {"stable": 0.1, "rising": 0.10},
        "2024-06": {"stable": 0.1, "rising": 0.15},
    }
    result = detect_emerging_topics(trends, window=3)

    # "rising" should be detected (acceleration > 2x)
    keywords = [r["keyword"] for r in result]
    assert "rising" in keywords

    # "stable" should NOT be detected (acceleration = 1.0)
    assert "stable" not in keywords

    # Check structure of results
    for item in result:
        assert "keyword" in item
        assert "recent_score" in item
        assert "historical_avg" in item
        assert "acceleration" in item
        assert item["acceleration"] > 2.0


def test_detect_emerging_topics_sorted_by_acceleration():
    trends = {
        "2024-01": {"fast": 0.01, "faster": 0.005},
        "2024-02": {"fast": 0.01, "faster": 0.005},
        "2024-03": {"fast": 0.01, "faster": 0.005},
        "2024-04": {"fast": 0.05, "faster": 0.08},
        "2024-05": {"fast": 0.05, "faster": 0.08},
        "2024-06": {"fast": 0.05, "faster": 0.08},
    }
    result = detect_emerging_topics(trends, window=3)
    if len(result) >= 2:
        # Results should be sorted by acceleration descending
        for i in range(len(result) - 1):
            assert result[i]["acceleration"] >= result[i + 1]["acceleration"]


# ── find_leading_blogs tests ──


def test_find_leading_blogs_empty_db():
    conn = _mem_db()
    result = find_leading_blogs(conn, "python")
    assert result == []
    conn.close()


def test_find_leading_blogs_no_match():
    conn = _mem_db()
    _seed_posts(conn)
    result = find_leading_blogs(conn, "nonexistent_xyz_keyword")
    assert result == []
    conn.close()


def test_find_leading_blogs_finds_mentions():
    conn = _mem_db()
    _seed_posts(conn)

    result = find_leading_blogs(conn, "machine learning")
    assert len(result) > 0

    blog_names = [r["blog_name"] for r in result]
    assert "Alpha Blog" in blog_names
    assert "Beta Blog" in blog_names

    # Alpha Blog mentioned it first (2024-01-15 vs 2024-02-15)
    assert result[0]["blog_name"] == "Alpha Blog"

    # Check structure
    for item in result:
        assert "blog_name" in item
        assert "first_mention" in item
        assert "mention_count" in item
        assert item["mention_count"] > 0
    conn.close()


def test_find_leading_blogs_counts_correctly():
    conn = _mem_db()
    _seed_posts(conn)

    result = find_leading_blogs(conn, "machine learning")
    alpha = next(r for r in result if r["blog_name"] == "Alpha Blog")
    beta = next(r for r in result if r["blog_name"] == "Beta Blog")

    # Alpha has 2 posts mentioning "machine learning"
    assert alpha["mention_count"] == 2
    # Beta has 1 post mentioning "machine learning"
    assert beta["mention_count"] == 1
    conn.close()


def test_find_leading_blogs_case_insensitive():
    conn = _mem_db()
    _seed_posts(conn)

    result_lower = find_leading_blogs(conn, "kubernetes")
    result_upper = find_leading_blogs(conn, "Kubernetes")

    assert len(result_lower) == len(result_upper)
    for r1, r2 in zip(result_lower, result_upper):
        assert r1["blog_name"] == r2["blog_name"]
        assert r1["mention_count"] == r2["mention_count"]
    conn.close()


def test_find_leading_blogs_sorted_by_first_mention():
    conn = _mem_db()
    _seed_posts(conn)

    result = find_leading_blogs(conn, "webassembly")
    if len(result) >= 2:
        for i in range(len(result) - 1):
            assert result[i]["first_mention"] <= result[i + 1]["first_mention"]
    conn.close()
