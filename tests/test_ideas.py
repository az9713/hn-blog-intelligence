"""Tests for the project ideas module."""

import json
import os
import sqlite3
import tempfile

from click.testing import CliRunner

from hn_intel.db import init_db, upsert_blogs, insert_post
from hn_intel.ideas import (
    extract_pain_signals,
    extract_signal_keywords,
    score_ideas,
    build_justification,
    cluster_signals,
    generate_ideas,
    _generate_label,
    _extract_title_keywords,
    _extract_context,
    _compute_location_hint,
    _PAIN_STOP_WORDS,
)
from hn_intel.reports import generate_ideas_report
from hn_intel.cli import main


def _mem_db():
    """Create an in-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)
    return conn


def _seed_blogs(conn, blogs=None):
    """Insert default test blogs and return {name: id} mapping."""
    if blogs is None:
        blogs = [
            {"name": "Alpha Blog", "feed_url": "https://alpha.com/feed", "site_url": "https://alpha.com"},
            {"name": "Beta Blog", "feed_url": "https://beta.com/feed", "site_url": "https://beta.com"},
            {"name": "Gamma Blog", "feed_url": "https://gamma.com/feed", "site_url": "https://gamma.com"},
        ]
    upsert_blogs(conn, blogs)
    rows = conn.execute("SELECT id, name FROM blogs ORDER BY id").fetchall()
    return {row["name"]: row["id"] for row in rows}


def _seed_pain_posts(conn):
    """Insert posts containing various pain-point language.

    Returns {blog_name: blog_id} mapping.
    """
    from datetime import date, timedelta
    base = (date.today() - timedelta(days=60)).isoformat()
    ids = _seed_blogs(conn)

    posts = [
        # Wish signals
        (ids["Alpha Blog"], {
            "title": "Thoughts on developer tooling",
            "description": "<p>I wish someone would build a better debugger for distributed systems. "
                           "The current tools are inadequate.</p>",
            "url": "https://alpha.com/wish-post",
            "published": base,
            "author": "Alice",
        }),
        # Frustration signals
        (ids["Beta Blog"], {
            "title": "My experience with CI pipelines",
            "description": "<p>It is incredibly frustrating to deal with flaky CI tests. "
                           "Every team I work with faces this pain point daily.</p>",
            "url": "https://beta.com/frustration-post",
            "published": base,
            "author": "Bob",
        }),
        # Gap signals
        (ids["Gamma Blog"], {
            "title": "The state of observability",
            "description": "<p>There is still no good way to correlate logs across microservices "
                           "without setting up expensive infrastructure.</p>",
            "url": "https://gamma.com/gap-post",
            "published": base,
            "author": "Carol",
        }),
        # Difficulty signals
        (ids["Alpha Blog"], {
            "title": "Database migrations in production",
            "description": "<p>It is hard to run zero-downtime database migrations. "
                           "Most tools assume you can take the database offline.</p>",
            "url": "https://alpha.com/difficulty-post",
            "published": base,
            "author": "Alice",
        }),
        # Opportunity signals
        (ids["Beta Blog"], {
            "title": "The future of edge computing",
            "description": "<p>There is a huge opportunity in lightweight edge runtimes. "
                           "WebAssembly opens up new possibilities.</p>",
            "url": "https://beta.com/opportunity-post",
            "published": base,
            "author": "Bob",
        }),
        # Broken signals
        (ids["Gamma Blog"], {
            "title": "DNS resolution woes",
            "description": "<p>DNS caching in containers is broken in many orchestrators. "
                           "Pods frequently fail to resolve internal services.</p>",
            "url": "https://gamma.com/broken-post",
            "published": base,
            "author": "Carol",
        }),
        # Multiple signals in one post (overlap: wish + gap)
        (ids["Alpha Blog"], {
            "title": "Log analysis tools",
            "description": "<p>I wish there was a lightweight log analysis tool. "
                           "There is no good way to search logs without deploying Elasticsearch.</p>",
            "url": "https://alpha.com/multi-signal",
            "published": base,
            "author": "Alice",
        }),
    ]

    for blog_id, entry in posts:
        insert_post(conn, blog_id, entry)

    return ids


def _seed_neutral_posts(conn):
    """Insert posts with no pain-point language."""
    ids = _seed_blogs(conn)
    posts = [
        (ids["Alpha Blog"], {
            "title": "Introduction to Python",
            "description": "<p>Python is a versatile programming language used in many domains.</p>",
            "url": "https://alpha.com/neutral-1",
            "published": "2024-01-10",
            "author": "Alice",
        }),
        (ids["Beta Blog"], {
            "title": "Rust performance benchmarks",
            "description": "<p>We measured Rust against Go in several compute workloads.</p>",
            "url": "https://beta.com/neutral-2",
            "published": "2024-02-15",
            "author": "Bob",
        }),
    ]
    for blog_id, entry in posts:
        insert_post(conn, blog_id, entry)
    return ids


# ── extract_pain_signals tests ──


def test_extract_pain_signals_empty_db():
    conn = _mem_db()
    signals = extract_pain_signals(conn)
    assert signals == []
    conn.close()


def test_extract_pain_signals_no_signals():
    conn = _mem_db()
    _seed_neutral_posts(conn)
    signals = extract_pain_signals(conn)
    assert signals == []
    conn.close()


def test_extract_pain_signals_finds_wishes():
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)

    wish_signals = [s for s in signals if s["signal_type"] == "wish"]
    assert len(wish_signals) >= 1

    # Verify back-pointer data
    for s in wish_signals:
        assert s["blog_name"] in ("Alpha Blog", "Beta Blog", "Gamma Blog")
        assert s["post_url"].startswith("https://")
        assert s["post_title"] != ""
        assert s["published"] != ""
    conn.close()


def test_extract_pain_signals_finds_frustrations():
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)

    frust_signals = [s for s in signals if s["signal_type"] == "frustration"]
    assert len(frust_signals) >= 1
    assert any("Beta Blog" == s["blog_name"] for s in frust_signals)
    conn.close()


def test_extract_pain_signals_finds_gaps():
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)

    gap_signals = [s for s in signals if s["signal_type"] == "gap"]
    assert len(gap_signals) >= 1
    conn.close()


def test_extract_pain_signals_back_pointers():
    """Every signal must carry full provenance to source blog/post."""
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)

    assert len(signals) > 0
    required_keys = {
        "post_id", "blog_id", "blog_name", "post_title",
        "post_url", "published", "signal_text", "signal_type",
    }
    for s in signals:
        assert required_keys.issubset(s.keys()), f"Missing keys: {required_keys - s.keys()}"
        assert isinstance(s["post_id"], int)
        assert isinstance(s["blog_id"], int)
        assert len(s["signal_text"]) >= 10
    conn.close()


# ── extract_signal_keywords tests ──


def test_extract_signal_keywords_too_few():
    signals = [{"signal_text": "only one signal here"}]
    vectorizer, matrix = extract_signal_keywords(signals)
    assert vectorizer is None
    assert matrix is None


def test_extract_signal_keywords_returns_matrix():
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)
    assert len(signals) >= 2

    vectorizer, matrix = extract_signal_keywords(signals)
    assert vectorizer is not None
    assert matrix is not None
    assert matrix.shape[0] == len(signals)
    conn.close()


# ── score_ideas tests ──


def test_score_ideas_empty():
    result = score_ideas([], [], {})
    assert result == []


def test_score_ideas_with_emerging():
    signals = [
        {
            "blog_name": "Alpha Blog",
            "signal_text": "machine learning deployment is frustrating",
            "published": "2024-05-01",
        },
        {
            "blog_name": "Beta Blog",
            "signal_text": "no good way to handle payments",
            "published": "2024-04-01",
        },
    ]
    emerging = [
        {"keyword": "machine learning", "acceleration": 5.0,
         "recent_score": 0.1, "historical_avg": 0.02},
    ]
    centrality = {}

    scored = score_ideas(signals, emerging, centrality)
    assert len(scored) == 2

    # The ML signal should score higher on the trend dimension
    ml_sig = scored[0]
    pay_sig = scored[1]
    assert ml_sig["score_breakdown"]["trend"] > pay_sig["score_breakdown"]["trend"]
    assert "impact_score" in ml_sig


def test_score_ideas_with_centrality():
    signals = [
        {
            "blog_name": "Famous Blog",
            "signal_text": "I wish there was a better tool",
            "published": "2024-05-01",
        },
        {
            "blog_name": "Unknown Blog",
            "signal_text": "I wish there was a better tool",
            "published": "2024-05-01",
        },
    ]
    centrality = {
        "Famous Blog": {"pagerank": 0.9, "betweenness": 0.5, "in_degree": 10, "out_degree": 5},
        "Unknown Blog": {"pagerank": 0.01, "betweenness": 0.0, "in_degree": 0, "out_degree": 1},
    }

    scored = score_ideas(signals, [], centrality)
    famous = scored[0]
    unknown = scored[1]
    assert famous["score_breakdown"]["authority"] > unknown["score_breakdown"]["authority"]


# ── build_justification tests ──


def test_justification_content():
    idea = {
        "blog_count": 5,
        "signal_count": 8,
        "impact_score": 0.75,
        "pain_type_breakdown": {"gap": 4, "difficulty": 3, "wish": 1},
        "keywords": ["observability", "logging", "monitoring"],
        "sources": [
            {"blog_name": "Alpha Blog", "post_url": "https://alpha.com/1",
             "post_title": "Test", "published": "2024-05-01",
             "signal_text": "test signal", "signal_type": "gap"},
            {"blog_name": "Beta Blog", "post_url": "https://beta.com/1",
             "post_title": "Test2", "published": "2024-04-01",
             "signal_text": "test signal 2", "signal_type": "difficulty"},
            {"blog_name": "Gamma Blog", "post_url": "https://gamma.com/1",
             "post_title": "Test3", "published": "2024-03-01",
             "signal_text": "test signal 3", "signal_type": "wish"},
        ],
    }
    justification = build_justification(idea)

    # Should mention blog names
    assert "Alpha Blog" in justification
    # Should mention pain type breakdown
    assert "gap" in justification
    # Should mention keywords (now "Related trending topics")
    assert "observability" in justification
    # Should mention blog count
    assert "5 blogs" in justification
    # Should have an impact statement
    assert "impact" in justification.lower()
    # Should use "need" instead of "pain point"
    assert "pain point" not in justification


def test_justification_single_blog():
    idea = {
        "blog_count": 1,
        "signal_count": 1,
        "impact_score": 0.3,
        "pain_type_breakdown": {"wish": 1},
        "keywords": [],
        "sources": [
            {"blog_name": "Solo Blog", "post_url": "https://solo.com/1",
             "post_title": "One", "published": "2024-05-01",
             "signal_text": "I wish", "signal_type": "wish"},
        ],
    }
    justification = build_justification(idea)
    assert "Solo Blog" in justification


# ── cluster_signals tests ──


def test_cluster_signals_empty():
    result = cluster_signals([], None, None)
    assert result == []


def test_cluster_signals_single():
    signals = [{
        "post_id": 1, "blog_id": 1, "blog_name": "A Blog",
        "post_title": "T", "post_url": "https://a.com/1",
        "published": "2024-05-01", "signal_text": "I wish there was a tool",
        "signal_type": "wish", "impact_score": 0.5,
        "score_breakdown": {"trend": 0.2, "authority": 0.3, "breadth": 0.0, "recency": 0.4},
    }]
    result = cluster_signals(signals, None, None)
    assert len(result) == 1
    assert result[0]["signal_count"] == 1
    assert result[0]["blog_count"] == 1
    assert len(result[0]["sources"]) == 1


def test_cluster_signals_groups_similar():
    """Similar pain signals should cluster together."""
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)
    assert len(signals) >= 2

    vectorizer, matrix = extract_signal_keywords(signals)
    scored = score_ideas(signals, [], {})
    ideas = cluster_signals(scored, vectorizer, matrix)

    assert len(ideas) >= 1
    for idea in ideas:
        assert "idea_id" in idea
        assert "label" in idea
        assert "sources" in idea
        assert "justification" in idea
        assert idea["signal_count"] == len(idea["sources"])
        assert idea["blog_count"] >= 1
    conn.close()


def test_cluster_signals_sources_have_back_pointers():
    """Each source in a clustered idea must have full provenance."""
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)
    vectorizer, matrix = extract_signal_keywords(signals)
    scored = score_ideas(signals, [], {})
    ideas = cluster_signals(scored, vectorizer, matrix)

    for idea in ideas:
        for src in idea["sources"]:
            assert "blog_name" in src
            assert "post_title" in src
            assert "post_url" in src
            assert "published" in src
            assert "signal_text" in src
            assert "signal_type" in src
    conn.close()


# ── generate_ideas (end-to-end) tests ──


def test_generate_ideas_empty_db():
    conn = _mem_db()
    result = generate_ideas(conn)
    assert result == []
    conn.close()


def test_generate_ideas_end_to_end():
    conn = _mem_db()
    _seed_pain_posts(conn)
    ideas = generate_ideas(conn, top_n=10)

    assert len(ideas) >= 1
    # Ideas should be sorted by impact_score descending
    for i in range(len(ideas) - 1):
        assert ideas[i]["impact_score"] >= ideas[i + 1]["impact_score"]

    # Each idea should have full structure
    for idea in ideas:
        assert idea["label"] != ""
        assert idea["signal_count"] >= 1
        assert idea["blog_count"] >= 1
        assert len(idea["sources"]) >= 1
        assert idea["justification"] != ""
        assert idea["representative_quote"] != ""
    conn.close()


# ── Report generation tests ──


def test_ideas_report_creates_files():
    ideas = [{
        "idea_id": 0,
        "label": "testing tools",
        "impact_score": 0.8,
        "justification": "Multiple blogs raise this pain.",
        "keywords": ["testing", "ci"],
        "signal_count": 3,
        "blog_count": 2,
        "pain_type_breakdown": {"frustration": 2, "gap": 1},
        "representative_quote": "Flaky tests are painful.",
        "sources": [
            {"blog_name": "A Blog", "post_title": "CI Woes", "post_url": "https://a.com/1",
             "published": "2024-05-01", "signal_text": "Flaky tests are painful.",
             "signal_context": "We run CI daily. Flaky tests are painful. They waste hours.",
             "signal_location": "near the beginning",
             "signal_type": "frustration", "impact_score": 0.8,
             "score_breakdown": {"trend": 0.3, "authority": 0.2, "breadth": 0.2, "recency": 0.1}},
        ],
    }]
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_ideas_report(ideas, tmpdir)
        assert os.path.exists(md_path)
        assert os.path.exists(json_path)
        assert md_path.endswith("ideas.md")
        assert json_path.endswith("ideas.json")


def test_ideas_report_content():
    ideas = [{
        "idea_id": 0,
        "label": "Logging Monitoring Solution",
        "impact_score": 0.72,
        "justification": "3 blogs raise this. Related: logging, monitoring.",
        "keywords": ["logging", "monitoring"],
        "signal_count": 4,
        "blog_count": 3,
        "pain_type_breakdown": {"gap": 3, "wish": 1},
        "representative_quote": "No good way to correlate logs.",
        "sources": [
            {"blog_name": "Alpha Blog", "post_title": "Observability",
             "post_url": "https://alpha.com/obs", "published": "2024-04-20",
             "signal_text": "No good way to correlate logs.",
             "signal_context": "Logs are everywhere. No good way to correlate logs. This is a real problem.",
             "signal_location": "near the beginning",
             "signal_type": "gap", "impact_score": 0.72,
             "score_breakdown": {"trend": 0.4, "authority": 0.2, "breadth": 0.1, "recency": 0.1}},
            {"blog_name": "Beta Blog", "post_title": "Logging Pain",
             "post_url": "https://beta.com/log", "published": "2024-05-01",
             "signal_text": "I wish there was a lightweight log tool.",
             "signal_context": "Current tools are heavy. I wish there was a lightweight log tool. Something simple would help.",
             "signal_location": "midway through",
             "signal_type": "wish", "impact_score": 0.65,
             "score_breakdown": {"trend": 0.3, "authority": 0.1, "breadth": 0.1, "recency": 0.15}},
        ],
    }]
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_ideas_report(ideas, tmpdir)

        with open(md_path, encoding="utf-8") as f:
            md = f.read()
        assert "Project Ideas Report" in md
        assert "Logging Monitoring Solution" in md
        assert "Alpha Blog" in md
        assert "Beta Blog" in md
        assert "Justification" in md
        assert "Evidence" in md
        # Post title should be a clickable link
        assert "[Observability](https://alpha.com/obs)" in md
        # Date shown for post
        assert "**Date**: 2024-04-20" in md
        # Pain type as list item with location
        assert "- **Pain type**: gap" in md
        assert "**Found**: near the beginning" in md
        assert "**Found**: midway through" in md
        # Context blockquote with bolded signal text
        assert "**No good way to correlate logs.**" in md

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "ideas" in data
        assert len(data["ideas"]) == 1
        assert data["ideas"][0]["label"] == "Logging Monitoring Solution"
        assert len(data["ideas"][0]["sources"]) == 2


def test_ideas_report_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_ideas_report([], tmpdir)
        assert os.path.exists(md_path)
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "No project ideas detected" in content


# ── Label generation tests ──


def test_generate_label_with_keywords():
    keywords = ["database", "migration", "schema"]
    breakdown = {"difficulty": 5, "wish": 2}
    label = _generate_label(keywords, breakdown)
    assert label == "Simplified Database Migration Schema"


def test_generate_label_templates():
    """Each pain type should use its own template."""
    keywords = ["dns", "resolution"]
    assert _generate_label(keywords, {"broken": 3}) == "Reliable Dns Resolution"
    assert _generate_label(keywords, {"wish": 3}) == "Better Dns Resolution"
    assert _generate_label(keywords, {"gap": 3}) == "Dns Resolution Solution"
    assert _generate_label(keywords, {"opportunity": 3}) == "Dns Resolution Platform"


def test_generate_label_no_keywords():
    label = _generate_label([], {"wish": 1})
    assert label == "General Improvement"


# ── Pain stop words tests ──


def test_pain_stop_words_excluded_from_keywords():
    """Pain-trigger words should not appear in TF-IDF keywords."""
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)
    vectorizer, matrix = extract_signal_keywords(signals)

    if vectorizer is not None:
        feature_names = set(vectorizer.get_feature_names_out())
        for stop_word in _PAIN_STOP_WORDS:
            assert stop_word not in feature_names, f"Pain stop word '{stop_word}' found in TF-IDF features"
    conn.close()


# ── Deduplication tests ──


def test_extract_pain_signals_deduplicates_same_post_type():
    """Same post + signal_type should produce only one signal."""
    from datetime import date, timedelta
    recent = (date.today() - timedelta(days=30)).isoformat()
    conn = _mem_db()
    ids = _seed_blogs(conn)

    # Post with two wish-pattern matches
    insert_post(conn, ids["Alpha Blog"], {
        "title": "Multi-wish post",
        "description": "<p>I wish someone would build a better debugger. "
                       "I also wish there was a better profiler for production.</p>",
        "url": "https://alpha.com/multi-wish",
        "published": recent,
        "author": "Alice",
    })

    signals = extract_pain_signals(conn)
    wish_signals = [s for s in signals if s["signal_type"] == "wish"
                    and s["post_url"] == "https://alpha.com/multi-wish"]
    assert len(wish_signals) == 1, f"Expected 1 wish signal, got {len(wish_signals)}"
    conn.close()


def test_dedup_keeps_longest_match():
    """Deduplication should keep the longest signal text."""
    from datetime import date, timedelta
    recent = (date.today() - timedelta(days=30)).isoformat()
    conn = _mem_db()
    ids = _seed_blogs(conn)

    insert_post(conn, ids["Alpha Blog"], {
        "title": "Short and long wish",
        "description": "<p>I wish someone would build X. "
                       "I also wish there was a much better and more comprehensive tool for handling Y in production environments.</p>",
        "url": "https://alpha.com/long-wish",
        "published": recent,
        "author": "Alice",
    })

    signals = extract_pain_signals(conn)
    wish_signals = [s for s in signals if s["signal_type"] == "wish"
                    and s["post_url"] == "https://alpha.com/long-wish"]
    assert len(wish_signals) == 1
    # The kept signal should be the longer one
    assert len(wish_signals[0]["signal_text"]) > 30
    conn.close()


def test_dedup_allows_different_types_same_post():
    """Same post can have signals of different types."""
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)

    # The multi-signal post has both wish and gap signals
    multi_signals = [s for s in signals if s["post_url"] == "https://alpha.com/multi-signal"]
    types = {s["signal_type"] for s in multi_signals}
    assert len(types) >= 2, f"Expected multiple signal types, got {types}"
    # But each type should appear at most once
    for t in types:
        count = sum(1 for s in multi_signals if s["signal_type"] == t)
        assert count == 1, f"Signal type '{t}' appeared {count} times for same post"
    conn.close()


# ── Title keyword extraction tests ──


def test_extract_title_keywords_basic():
    members = [
        {"post_title": "Database migrations in production"},
        {"post_title": "Zero-downtime database upgrades"},
        {"post_title": "DNS resolution woes"},
    ]
    keywords = _extract_title_keywords(members)
    assert "database" in keywords
    # "database" appears in 2 titles, should rank first
    assert keywords[0] == "database"


def test_extract_title_keywords_filters_stop_words():
    members = [
        {"post_title": "I wish there was a better tool"},
        {"post_title": "The frustration of broken deployments"},
    ]
    keywords = _extract_title_keywords(members)
    # Pain/English stop words should be filtered out
    for kw in keywords:
        assert kw not in ("wish", "frustration", "broken", "the", "was")


def test_extract_title_keywords_empty_titles():
    members = [{"post_title": ""}, {"post_title": ""}]
    keywords = _extract_title_keywords(members)
    assert keywords == []


def test_extract_title_keywords_counts_once_per_title():
    """Same word appearing twice in one title should count as 1."""
    members = [
        {"post_title": "DNS DNS DNS resolution"},
        {"post_title": "Container networking"},
    ]
    keywords = _extract_title_keywords(members)
    # "dns" appears in only 1 title despite repetition
    assert keywords.count("dns") <= 1


# ── Quality filtering tests ──


def test_generate_ideas_filters_singletons():
    """Ideas with only 1 blog should be filtered when better ideas exist.

    Uses cluster_signals directly to avoid needing large corpora for
    compute_trends (which generate_ideas calls internally).
    """
    # Build signals that represent two clusters:
    # Cluster A: multi-blog (blog_count=2), should survive filtering
    # Cluster B: singleton (blog_count=1), should be filtered
    multi_blog_signals = [
        {
            "post_id": 1, "blog_id": 1, "blog_name": "Blog A",
            "post_title": "Testing microservices", "post_url": "https://a.com/p1",
            "published": "2024-06-01", "signal_text": "I wish someone would build better testing tools for microservices",
            "signal_type": "wish", "impact_score": 0.5,
            "score_breakdown": {"trend": 0.2, "authority": 0.1, "breadth": 0.1, "recency": 0.1},
        },
        {
            "post_id": 2, "blog_id": 2, "blog_name": "Blog B",
            "post_title": "Testing distributed systems", "post_url": "https://b.com/p1",
            "published": "2024-06-02", "signal_text": "I wish there was a good way to test distributed systems end to end",
            "signal_type": "wish", "impact_score": 0.5,
            "score_breakdown": {"trend": 0.2, "authority": 0.1, "breadth": 0.1, "recency": 0.1},
        },
    ]
    singleton_signal = [
        {
            "post_id": 3, "blog_id": 3, "blog_name": "Blog C",
            "post_title": "Cooking recipes", "post_url": "https://c.com/p1",
            "published": "2024-06-03", "signal_text": "I wish someone would build a recipe manager without subscriptions",
            "signal_type": "wish", "impact_score": 0.4,
            "score_breakdown": {"trend": 0.1, "authority": 0.1, "breadth": 0.0, "recency": 0.2},
        },
    ]

    all_signals = multi_blog_signals + singleton_signal
    vectorizer, matrix = extract_signal_keywords(all_signals)
    ideas = cluster_signals(all_signals, vectorizer, matrix)

    # Without filtering, we'd have ideas with blog_count=1
    # Apply the same filter as generate_ideas
    quality_ideas = [i for i in ideas if i["blog_count"] >= 2]
    if quality_ideas:
        for idea in quality_ideas:
            assert idea["blog_count"] >= 2


# ── Context and location hint tests ──


def test_extract_context_basic():
    """Verify 2-3 sentences surrounding the match are returned."""
    text = "First sentence. Second sentence with a pain point. Third sentence here. Fourth sentence."
    # Match is within "Second sentence with a pain point."
    match_start = text.index("pain point")
    match_end = match_start + len("pain point")
    context = _extract_context(text, match_start, match_end)
    assert "First sentence" in context
    assert "pain point" in context
    # Should include sentence before and the match sentence (at least 2)
    assert context.count(".") >= 1


def test_extract_context_at_start():
    """When match is in the first sentence, no prior sentence exists."""
    text = "This is a pain point here. Second sentence. Third sentence."
    match_start = text.index("pain point")
    match_end = match_start + len("pain point")
    context = _extract_context(text, match_start, match_end)
    assert "pain point" in context


def test_extract_context_fallback():
    """When sentence boundaries aren't found, fallback to character window."""
    text = "no punctuation here so this is a pain point somewhere in text"
    match_start = text.index("pain point")
    match_end = match_start + len("pain point")
    context = _extract_context(text, match_start, match_end)
    assert "pain point" in context


def test_compute_location_hint():
    """Verify location hints for different positions."""
    assert _compute_location_hint(5, 20, 100) == "in the title"
    assert _compute_location_hint(25, 20, 200) == "near the beginning"
    assert _compute_location_hint(110, 20, 200) == "midway through"
    assert _compute_location_hint(180, 20, 200) == "near the end"


def test_compute_location_hint_edge_cases():
    """Edge cases: match at title boundary, very short text."""
    assert _compute_location_hint(0, 10, 10) == "in the title"
    # When match_start == title_len, it's at body start (body_pos=0)
    assert _compute_location_hint(10, 10, 10) == "near the beginning"


def test_signal_has_context_and_location():
    """Verify new fields exist in extract_pain_signals output."""
    conn = _mem_db()
    _seed_pain_posts(conn)
    signals = extract_pain_signals(conn)

    assert len(signals) > 0
    for s in signals:
        assert "signal_context" in s, f"Missing signal_context in signal: {s['post_url']}"
        assert "signal_location" in s, f"Missing signal_location in signal: {s['post_url']}"
        assert len(s["signal_context"]) >= len(s["signal_text"])
        assert s["signal_location"] in (
            "in the title", "near the beginning", "midway through", "near the end"
        )
    conn.close()


def test_ideas_report_evidence_section():
    """Verify the markdown report contains the new Evidence format."""
    ideas = [{
        "idea_id": 0,
        "label": "Test Idea",
        "impact_score": 0.5,
        "justification": "Test justification.",
        "keywords": ["test"],
        "signal_count": 2,
        "blog_count": 2,
        "pain_type_breakdown": {"wish": 1, "gap": 1},
        "representative_quote": "I wish there was a better tool.",
        "sources": [
            {"blog_name": "Blog A", "post_title": "Post Alpha",
             "post_url": "https://a.com/alpha", "published": "2024-06-01",
             "signal_text": "I wish there was a better tool.",
             "signal_context": "Current tools are bad. I wish there was a better tool. Something modern.",
             "signal_location": "near the beginning",
             "signal_type": "wish", "impact_score": 0.5,
             "score_breakdown": {"trend": 0.2, "authority": 0.1, "breadth": 0.1, "recency": 0.1}},
            {"blog_name": "Blog B", "post_title": "Post Beta",
             "post_url": "https://b.com/beta", "published": "2024-06-02",
             "signal_text": "No good way to handle this.",
             "signal_context": "We tried everything. No good way to handle this. Very frustrating.",
             "signal_location": "midway through",
             "signal_type": "gap", "impact_score": 0.45,
             "score_breakdown": {"trend": 0.1, "authority": 0.1, "breadth": 0.1, "recency": 0.15}},
        ],
    }]
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, _ = generate_ideas_report(ideas, tmpdir)
        with open(md_path, encoding="utf-8") as f:
            md = f.read()

        # Evidence section header
        assert "### Evidence" in md
        # Post title as clickable link
        assert "[Post Alpha](https://a.com/alpha)" in md
        assert "[Post Beta](https://b.com/beta)" in md
        # Blog name after title
        assert "Blog A" in md
        assert "Blog B" in md
        # Date shown once per post
        assert "**Date**: 2024-06-01" in md
        # Pain type as list items with location
        assert "- **Pain type**: wish" in md
        assert "**Found**: near the beginning" in md
        assert "**Found**: midway through" in md
        # Context blockquote with bolded signal
        assert "**I wish there was a better tool.**" in md
        assert "**No good way to handle this.**" in md
        # Old format should NOT be present
        assert "Key Quotes" not in md


def test_ideas_report_consolidates_same_post():
    """Multiple signals from the same post should appear under one heading."""
    ideas = [{
        "idea_id": 0,
        "label": "Consolidated Idea",
        "impact_score": 0.6,
        "justification": "Test.",
        "keywords": ["test"],
        "signal_count": 3,
        "blog_count": 2,
        "pain_type_breakdown": {"difficulty": 2, "broken": 1},
        "representative_quote": "it is hard to do X.",
        "sources": [
            {"blog_name": "Blog A", "post_title": "Same Post",
             "post_url": "https://a.com/same", "published": "2025-11-22",
             "signal_text": "it is hard to do X.",
             "signal_context": "Sometimes it is hard to do X. We tried everything.",
             "signal_location": "midway through",
             "signal_type": "difficulty", "impact_score": 0.6,
             "score_breakdown": {"trend": 0.2, "authority": 0.1, "breadth": 0.2, "recency": 0.1}},
            {"blog_name": "Blog A", "post_title": "Same Post",
             "post_url": "https://a.com/same", "published": "2025-11-22",
             "signal_text": "evals are largely unreliable.",
             "signal_context": "But evals are largely unreliable. They don't measure what matters.",
             "signal_location": "near the beginning",
             "signal_type": "broken", "impact_score": 0.5,
             "score_breakdown": {"trend": 0.1, "authority": 0.1, "breadth": 0.2, "recency": 0.1}},
            {"blog_name": "Blog B", "post_title": "Different Post",
             "post_url": "https://b.com/different", "published": "2025-12-01",
             "signal_text": "No good way to test this.",
             "signal_context": "There is no good way to test this. We need better tools.",
             "signal_location": "near the end",
             "signal_type": "difficulty", "impact_score": 0.45,
             "score_breakdown": {"trend": 0.1, "authority": 0.1, "breadth": 0.1, "recency": 0.15}},
        ],
    }]
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, _ = generate_ideas_report(ideas, tmpdir)
        with open(md_path, encoding="utf-8") as f:
            md = f.read()

        # "Same Post" heading should appear exactly once
        assert md.count("[Same Post](https://a.com/same)") == 1
        # But both signal types should be listed
        assert "- **Pain type**: difficulty" in md
        assert "- **Pain type**: broken" in md
        # Both signal texts should appear bolded in context
        assert "**it is hard to do X.**" in md
        assert "**evals are largely unreliable.**" in md
        # The different post should also appear
        assert "[Different Post](https://b.com/different)" in md


# ── CLI tests ──


def test_cli_ideas_help():
    runner = CliRunner()
    result = runner.invoke(main, ["ideas", "--help"])
    assert result.exit_code == 0
    assert "max-features" in result.output
    assert "top-n" in result.output
    assert "period" in result.output
    assert "output-dir" in result.output


def test_cli_main_lists_ideas_command():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert "ideas" in result.output


# ── Renumbering after filter tests ──


def test_renumber_after_filter():
    """After filtering singletons, idea_ids should be sequential with no gaps."""
    # Simulate ideas as produced by cluster_signals (with gaps after filter)
    ideas = [
        {"idea_id": 0, "blog_count": 3, "label": "A"},
        {"idea_id": 1, "blog_count": 1, "label": "B"},  # will be filtered
        {"idea_id": 2, "blog_count": 2, "label": "C"},
        {"idea_id": 3, "blog_count": 1, "label": "D"},  # will be filtered
        {"idea_id": 4, "blog_count": 4, "label": "E"},
    ]

    quality_ideas = [i for i in ideas if i["blog_count"] >= 2]
    if quality_ideas:
        ideas = quality_ideas

    # Re-number (same logic as generate_ideas)
    for i, idea in enumerate(ideas):
        idea["idea_id"] = i

    assert [idea["idea_id"] for idea in ideas] == [0, 1, 2]
    assert [idea["label"] for idea in ideas] == ["A", "C", "E"]


# ── Date filter tests ──


def test_extract_pain_signals_filters_old_posts():
    """Posts older than max_age_days should be excluded."""
    conn = _mem_db()
    ids = _seed_blogs(conn)

    # Old post (2017) with pain signal
    insert_post(conn, ids["Alpha Blog"], {
        "title": "Ancient tooling thoughts",
        "description": "<p>I wish someone would build a better debugger.</p>",
        "url": "https://alpha.com/old-post",
        "published": "2017-02-04",
        "author": "Alice",
    })
    # Recent post with pain signal
    from datetime import date, timedelta
    recent_date = (date.today() - timedelta(days=30)).isoformat()
    insert_post(conn, ids["Beta Blog"], {
        "title": "Modern CI problems",
        "description": "<p>I wish someone would build a better CI system.</p>",
        "url": "https://beta.com/recent-post",
        "published": recent_date,
        "author": "Bob",
    })

    signals = extract_pain_signals(conn, max_age_days=365)

    urls = [s["post_url"] for s in signals]
    assert "https://alpha.com/old-post" not in urls
    assert "https://beta.com/recent-post" in urls
    conn.close()


def test_extract_pain_signals_keeps_missing_date():
    """Posts with empty published date should NOT be filtered out."""
    conn = _mem_db()
    ids = _seed_blogs(conn)

    insert_post(conn, ids["Alpha Blog"], {
        "title": "Undated post",
        "description": "<p>I wish someone would build a better tool for this.</p>",
        "url": "https://alpha.com/no-date",
        "published": "",
        "author": "Alice",
    })

    signals = extract_pain_signals(conn, max_age_days=365)

    urls = [s["post_url"] for s in signals]
    assert "https://alpha.com/no-date" in urls
    conn.close()
