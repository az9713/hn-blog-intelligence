"""Tests for the report generation module."""

import json
import os
import sqlite3
import tempfile

import networkx as nx
import numpy as np
from click.testing import CliRunner

from hn_intel.db import init_db, upsert_blogs, insert_post
from hn_intel.reports import (
    generate_summary_report,
    generate_trend_report,
    generate_network_report,
    generate_cluster_report,
    generate_all_reports,
)
from hn_intel.cli import main


def _mem_db():
    """Create an in-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)
    return conn


def _seed_data(conn):
    """Insert test blogs and posts, returning blog IDs."""
    upsert_blogs(conn, [
        {"name": "Alpha Blog", "feed_url": "https://alpha.com/feed", "site_url": "https://alpha.com"},
        {"name": "Beta Blog", "feed_url": "https://beta.com/feed", "site_url": "https://beta.com"},
        {"name": "Gamma Blog", "feed_url": "https://gamma.com/feed", "site_url": "https://gamma.com"},
    ])
    rows = conn.execute("SELECT id, name FROM blogs ORDER BY id").fetchall()
    ids = {row["name"]: row["id"] for row in rows}

    posts = [
        (ids["Alpha Blog"], {"title": "ML intro", "description": "<p>Machine learning basics</p>",
         "url": "https://alpha.com/1", "published": "2024-01-10", "author": "A"}),
        (ids["Alpha Blog"], {"title": "Deep learning", "description": "<p>Neural network intro</p>",
         "url": "https://alpha.com/2", "published": "2024-02-10", "author": "A"}),
        (ids["Beta Blog"], {"title": "Python tips", "description": "<p>Python programming</p>",
         "url": "https://beta.com/1", "published": "2024-01-15", "author": "B"}),
        (ids["Beta Blog"], {"title": "Rust lang", "description": "<p>Rust programming guide</p>",
         "url": "https://beta.com/2", "published": "2024-03-10", "author": "B"}),
        (ids["Gamma Blog"], {"title": "WebAssembly", "description": "<p>WASM performance</p>",
         "url": "https://gamma.com/1", "published": "2024-02-20", "author": "C"}),
    ]
    for blog_id, entry in posts:
        insert_post(conn, blog_id, entry)

    return ids


def _sample_trends():
    """Return sample trend data."""
    return {
        "2024-01": {"machine": 0.3, "python": 0.2},
        "2024-02": {"machine": 0.4, "neural": 0.3},
        "2024-03": {"rust": 0.5, "python": 0.1},
    }


def _sample_emerging():
    """Return sample emerging topics."""
    return [
        {"keyword": "rust", "recent_score": 0.5, "historical_avg": 0.1, "acceleration": 5.0},
        {"keyword": "wasm", "recent_score": 0.3, "historical_avg": 0.05, "acceleration": 6.0},
    ]


def _sample_centrality():
    """Return sample centrality data."""
    return {
        "Alpha Blog": {"pagerank": 0.45, "betweenness": 0.3, "in_degree": 2, "out_degree": 1},
        "Beta Blog": {"pagerank": 0.35, "betweenness": 0.1, "in_degree": 1, "out_degree": 1},
        "Gamma Blog": {"pagerank": 0.20, "betweenness": 0.0, "in_degree": 0, "out_degree": 1},
    }


def _sample_graph():
    """Return a sample directed graph."""
    graph = nx.DiGraph()
    graph.add_node(1, name="Alpha Blog")
    graph.add_node(2, name="Beta Blog")
    graph.add_node(3, name="Gamma Blog")
    graph.add_edge(1, 2, weight=2)
    graph.add_edge(2, 1, weight=1)
    graph.add_edge(3, 1, weight=1)
    return graph


def _sample_clusters():
    """Return sample cluster results."""
    return [
        {"cluster_id": 0, "label": "machine, learning, neural, deep, model", "blogs": ["Alpha Blog"]},
        {"cluster_id": 1, "label": "python, rust, programming, code, lang", "blogs": ["Beta Blog", "Gamma Blog"]},
    ]


def _sample_similarity():
    """Return a sample similarity matrix and blog names."""
    blog_names = ["Alpha Blog", "Beta Blog", "Gamma Blog"]
    sim_matrix = np.array([
        [1.0, 0.3, 0.2],
        [0.3, 1.0, 0.7],
        [0.2, 0.7, 1.0],
    ])
    return sim_matrix, blog_names


# ── generate_summary_report tests ──


def test_summary_report_creates_file():
    conn = _mem_db()
    _seed_data(conn)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_summary_report(
            _sample_trends(), _sample_emerging(), _sample_centrality(),
            _sample_clusters(), conn, tmpdir,
        )
        assert os.path.exists(path)
        assert path.endswith("summary.md")
    conn.close()


def test_summary_report_content():
    conn = _mem_db()
    _seed_data(conn)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_summary_report(
            _sample_trends(), _sample_emerging(), _sample_centrality(),
            _sample_clusters(), conn, tmpdir,
        )
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Dataset Overview" in content
        assert "Blogs" in content
        assert "Posts" in content
        assert "Emerging Topics" in content
        assert "rust" in content
        assert "Alpha Blog" in content
        assert "Blog Clusters" in content
    conn.close()


def test_summary_report_empty_data():
    conn = _mem_db()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = generate_summary_report({}, [], {}, [], conn, tmpdir)
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "No emerging topics" in content
        assert "No citation data" in content
        assert "No cluster data" in content
    conn.close()


# ── generate_trend_report tests ──


def test_trend_report_creates_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_trend_report(
            _sample_trends(), _sample_emerging(), tmpdir,
        )
        assert os.path.exists(md_path)
        assert os.path.exists(json_path)
        assert md_path.endswith("trends.md")
        assert json_path.endswith("trends.json")


def test_trend_report_md_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, _ = generate_trend_report(
            _sample_trends(), _sample_emerging(), tmpdir,
        )
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "Trend Analysis" in content
        assert "Emerging Topics" in content
        assert "rust" in content


def test_trend_report_json_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        _, json_path = generate_trend_report(
            _sample_trends(), _sample_emerging(), tmpdir,
        )
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "periods" in data
        assert "emerging_topics" in data
        assert "2024-01" in data["periods"]
        assert len(data["emerging_topics"]) == 2


def test_trend_report_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_trend_report({}, [], tmpdir)
        assert os.path.exists(md_path)
        assert os.path.exists(json_path)
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "No emerging topics" in content


# ── generate_network_report tests ──


def test_network_report_creates_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_network_report(
            _sample_centrality(), _sample_graph(), tmpdir,
        )
        assert os.path.exists(md_path)
        assert os.path.exists(json_path)


def test_network_report_md_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, _ = generate_network_report(
            _sample_centrality(), _sample_graph(), tmpdir,
        )
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "Network Analysis" in content
        assert "Nodes (blogs)" in content
        assert "3" in content  # node count
        assert "Alpha Blog" in content
        assert "PageRank" in content
        assert "Betweenness" in content


def test_network_report_json_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        _, json_path = generate_network_report(
            _sample_centrality(), _sample_graph(), tmpdir,
        )
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["graph_stats"]["nodes"] == 3
        assert data["graph_stats"]["edges"] == 3
        assert "density" in data["graph_stats"]
        assert "Alpha Blog" in data["centrality"]


def test_network_report_empty_graph():
    graph = nx.DiGraph()
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_network_report({}, graph, tmpdir)
        assert os.path.exists(md_path)
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "No centrality data" in content


# ── generate_cluster_report tests ──


def test_cluster_report_creates_files():
    sim_matrix, blog_names = _sample_similarity()
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_cluster_report(
            _sample_clusters(), sim_matrix, blog_names, tmpdir,
        )
        assert os.path.exists(md_path)
        assert os.path.exists(json_path)


def test_cluster_report_md_content():
    sim_matrix, blog_names = _sample_similarity()
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, _ = generate_cluster_report(
            _sample_clusters(), sim_matrix, blog_names, tmpdir,
        )
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "Cluster Report" in content
        assert "Cluster 0" in content
        assert "Alpha Blog" in content
        assert "Similar Blog Pairs" in content


def test_cluster_report_json_content():
    sim_matrix, blog_names = _sample_similarity()
    with tempfile.TemporaryDirectory() as tmpdir:
        _, json_path = generate_cluster_report(
            _sample_clusters(), sim_matrix, blog_names, tmpdir,
        )
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "clusters" in data
        assert "blog_similarities" in data
        assert len(data["clusters"]) == 2
        assert "Alpha Blog" in data["blog_similarities"]


def test_cluster_report_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path, json_path = generate_cluster_report([], None, [], tmpdir)
        assert os.path.exists(md_path)
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "No cluster data" in content


# ── generate_all_reports tests ──


def test_all_reports_creates_all_files():
    conn = _mem_db()
    _seed_data(conn)
    sim_matrix, blog_names = _sample_similarity()
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = generate_all_reports(
            trends=_sample_trends(),
            emerging=_sample_emerging(),
            centrality=_sample_centrality(),
            graph=_sample_graph(),
            cluster_results=_sample_clusters(),
            similarity_matrix=sim_matrix,
            blog_names=blog_names,
            conn=conn,
            output_dir=tmpdir,
        )
        assert len(paths) == 7  # summary.md + 3 pairs of (md, json)
        for path in paths:
            assert os.path.exists(path)
    conn.close()


def test_all_reports_output_dir_created():
    conn = _mem_db()
    sim_matrix, blog_names = _sample_similarity()
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_dir = os.path.join(tmpdir, "nested", "output")
        paths = generate_all_reports(
            trends={}, emerging=[], centrality={},
            graph=nx.DiGraph(), cluster_results=[],
            similarity_matrix=None, blog_names=[],
            conn=conn, output_dir=nested_dir,
        )
        assert os.path.isdir(nested_dir)
        assert len(paths) == 7
    conn.close()


# ── CLI integration tests ──


def test_cli_analyze_help():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "max-features" in result.output
    assert "n-clusters" in result.output
    assert "period" in result.output


def test_cli_report_help():
    runner = CliRunner()
    result = runner.invoke(main, ["report", "--help"])
    assert result.exit_code == 0
    assert "output-dir" in result.output
    assert "max-features" in result.output
    assert "period" in result.output


def test_cli_main_group_lists_commands():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output
    assert "report" in result.output
    assert "fetch" in result.output
    assert "status" in result.output
