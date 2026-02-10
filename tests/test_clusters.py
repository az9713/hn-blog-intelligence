"""Tests for blog clustering module."""

import sqlite3
import os
import tempfile

from hn_intel.db import init_db, upsert_blogs, insert_post
from hn_intel.clusters import (
    strip_html,
    compute_blog_vectors,
    compute_similarity_matrix,
    find_similar_blogs,
    cluster_blogs,
)


def _temp_db():
    """Create a temporary database connection."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn, path


def _seed_blogs(conn):
    """Seed the database with test blogs covering distinct topics.

    Creates 4 blogs:
      - Python Blog and Data Science Blog (programming/ML overlap)
      - Cooking Blog (food topic)
      - Baking Blog (food topic, similar to cooking)
    """
    blogs = [
        {"name": "Python Blog", "feed_url": "https://python.com/feed", "site_url": "https://python.com"},
        {"name": "Data Science Blog", "feed_url": "https://datascience.com/feed", "site_url": "https://datascience.com"},
        {"name": "Cooking Blog", "feed_url": "https://cooking.com/feed", "site_url": "https://cooking.com"},
        {"name": "Baking Blog", "feed_url": "https://baking.com/feed", "site_url": "https://baking.com"},
    ]
    upsert_blogs(conn, blogs)

    rows = conn.execute("SELECT id, name FROM blogs ORDER BY id").fetchall()
    blog_ids = {row["name"]: row["id"] for row in rows}

    # Python Blog posts
    for i, (title, desc) in enumerate([
        ("Python decorators explained", "Learn about <b>Python</b> decorators, functions, and closures in this tutorial"),
        ("Async programming in Python", "Understanding <em>asyncio</em>, coroutines, and event loops in Python programming"),
        ("Python type hints guide", "Static typing with Python type hints improves code quality and developer experience"),
    ]):
        insert_post(conn, blog_ids["Python Blog"], {
            "title": title, "description": desc,
            "url": f"https://python.com/post-{i}", "published": "2024-01-01", "author": "Author",
        })

    # Data Science Blog posts
    for i, (title, desc) in enumerate([
        ("Machine learning with Python", "Using <b>scikit-learn</b> and Python for machine learning models and data analysis"),
        ("Data analysis with pandas", "Python pandas library for data manipulation, cleaning, and statistical analysis"),
        ("Neural networks introduction", "Deep learning neural networks with Python TensorFlow for data science applications"),
    ]):
        insert_post(conn, blog_ids["Data Science Blog"], {
            "title": title, "description": desc,
            "url": f"https://datascience.com/post-{i}", "published": "2024-01-01", "author": "Author",
        })

    # Cooking Blog posts
    for i, (title, desc) in enumerate([
        ("Italian pasta recipes", "Delicious <b>pasta</b> recipes with fresh ingredients, tomato sauce, and herbs"),
        ("Grilling techniques", "Master the art of grilling meat, vegetables, and seafood with proper cooking temperatures"),
        ("Healthy salad ideas", "Fresh salad recipes with nutritious ingredients for healthy meals and cooking"),
    ]):
        insert_post(conn, blog_ids["Cooking Blog"], {
            "title": title, "description": desc,
            "url": f"https://cooking.com/post-{i}", "published": "2024-01-01", "author": "Author",
        })

    # Baking Blog posts
    for i, (title, desc) in enumerate([
        ("Sourdough bread recipe", "How to bake the perfect <b>sourdough</b> bread with flour, yeast, and fresh ingredients"),
        ("Chocolate cake from scratch", "Baking a rich chocolate cake with cocoa, sugar, and butter for delicious desserts"),
        ("Cookie recipes collection", "Classic cookie recipes including sugar cookies, oatmeal, and chocolate chip baking"),
    ]):
        insert_post(conn, blog_ids["Baking Blog"], {
            "title": title, "description": desc,
            "url": f"https://baking.com/post-{i}", "published": "2024-01-01", "author": "Author",
        })


def test_strip_html():
    assert strip_html("<b>bold</b> text") == "bold  text"
    assert strip_html(None) == ""
    assert strip_html("") == ""
    assert strip_html("no tags") == "no tags"
    assert strip_html("<p>hello</p><br/>world") == "hello  world"


def test_compute_blog_vectors():
    conn, path = _temp_db()
    try:
        init_db(conn)
        _seed_blogs(conn)

        matrix, names, vectorizer = compute_blog_vectors(conn)

        assert len(names) == 4
        assert matrix.shape[0] == 4
        assert matrix.shape[1] <= 500
        assert "Baking Blog" in names
        assert "Python Blog" in names
        # Names should be sorted
        assert names == sorted(names)
    finally:
        conn.close()
        os.unlink(path)


def test_compute_similarity_matrix():
    conn, path = _temp_db()
    try:
        init_db(conn)
        _seed_blogs(conn)

        matrix, names, _ = compute_blog_vectors(conn)
        sim = compute_similarity_matrix(matrix)

        assert sim.shape == (4, 4)
        # Diagonal should be 1.0 (self-similarity)
        for i in range(4):
            assert abs(sim[i][i] - 1.0) < 1e-6
        # Similarity values should be between 0 and 1
        assert sim.min() >= -1e-6
        assert sim.max() <= 1.0 + 1e-6
    finally:
        conn.close()
        os.unlink(path)


def test_find_similar_blogs():
    conn, path = _temp_db()
    try:
        init_db(conn)
        _seed_blogs(conn)

        matrix, names, _ = compute_blog_vectors(conn)
        sim = compute_similarity_matrix(matrix)

        # Python Blog should be most similar to Data Science Blog
        similar = find_similar_blogs(sim, names, "Python Blog", top_n=3)
        assert len(similar) == 3
        assert similar[0]["name"] == "Data Science Blog"
        assert similar[0]["similarity_score"] > 0.0

        # Cooking Blog should be most similar to Baking Blog
        similar = find_similar_blogs(sim, names, "Cooking Blog", top_n=3)
        assert similar[0]["name"] == "Baking Blog"

        # Non-existent blog returns empty list
        assert find_similar_blogs(sim, names, "No Such Blog") == []
    finally:
        conn.close()
        os.unlink(path)


def test_find_similar_blogs_excludes_self():
    conn, path = _temp_db()
    try:
        init_db(conn)
        _seed_blogs(conn)

        matrix, names, _ = compute_blog_vectors(conn)
        sim = compute_similarity_matrix(matrix)

        similar = find_similar_blogs(sim, names, "Python Blog", top_n=5)
        result_names = [s["name"] for s in similar]
        assert "Python Blog" not in result_names
    finally:
        conn.close()
        os.unlink(path)


def test_cluster_blogs():
    conn, path = _temp_db()
    try:
        init_db(conn)
        _seed_blogs(conn)

        matrix, names, vectorizer = compute_blog_vectors(conn)
        clusters = cluster_blogs(matrix, names, vectorizer, n_clusters=2)

        assert len(clusters) == 2
        # Every blog should appear in exactly one cluster
        all_blogs = []
        for c in clusters:
            assert "cluster_id" in c
            assert "label" in c
            assert "blogs" in c
            assert len(c["label"]) > 0
            all_blogs.extend(c["blogs"])
        assert sorted(all_blogs) == sorted(names)

        # Programming blogs should be in one cluster, food blogs in another
        for c in clusters:
            blog_set = set(c["blogs"])
            if "Python Blog" in blog_set:
                assert "Data Science Blog" in blog_set
            if "Cooking Blog" in blog_set:
                assert "Baking Blog" in blog_set
    finally:
        conn.close()
        os.unlink(path)


def test_cluster_blogs_caps_k():
    conn, path = _temp_db()
    try:
        init_db(conn)
        _seed_blogs(conn)

        matrix, names, vectorizer = compute_blog_vectors(conn)
        # Requesting more clusters than blogs should cap at len(blogs)
        clusters = cluster_blogs(matrix, names, vectorizer, n_clusters=100)
        assert len(clusters) == len(names)
    finally:
        conn.close()
        os.unlink(path)


def test_cluster_labels_contain_keywords():
    conn, path = _temp_db()
    try:
        init_db(conn)
        _seed_blogs(conn)

        matrix, names, vectorizer = compute_blog_vectors(conn)
        clusters = cluster_blogs(matrix, names, vectorizer, n_clusters=2)

        for c in clusters:
            # Label should be comma-separated keywords
            keywords = c["label"].split(", ")
            assert len(keywords) == 5
    finally:
        conn.close()
        os.unlink(path)
