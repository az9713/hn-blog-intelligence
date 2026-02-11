# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable mode with dev deps)
pip install -e ".[dev]"

# CLI (entry point: hn_intel.cli:main)
hn-intel fetch                # Fetch RSS feeds → SQLite
hn-intel status               # Show DB stats
hn-intel analyze              # Run analysis, print summary
hn-intel ideas                # Surface project ideas from pain signals
hn-intel report               # Run analysis + generate all reports to output/

# Testing (97 tests, all use in-memory SQLite)
python -m pytest tests/ -v
python -m pytest tests/test_analyzer.py -v                    # Single file
python -m pytest tests/test_analyzer.py::test_compute_trends -v  # Single test
```

## Architecture

Python CLI tool analyzing 92 HN popular blog RSS feeds. Pipeline: OPML → fetch → SQLite → analysis → reports.

**Data flow**: `opml_parser` → `fetcher` (stores to DB) → analysis modules (`analyzer`, `network`, `clusters`, `ideas`) all read from SQLite via `db.get_all_posts()` → `reports` writes Markdown + JSON to `output/`.

**Key design decisions**:
- All analysis modules receive a `sqlite3.Connection` and call `get_all_posts(conn)` which returns `sqlite3.Row` objects (dict-like access: `row["title"]`)
- `description` field stores **raw HTML** (needed for citation link extraction in `network.py`). Always call `strip_html()` before text analysis.
- `strip_html()` is intentionally duplicated in `analyzer.py`, `clusters.py`, and `ideas.py` (each has its own copy)
- CLI uses **lazy imports** inside command functions to avoid loading sklearn/networkx at startup
- Every CLI command opens/closes its own DB connection via `get_connection()` + `init_db(conn)`
- Post deduplication uses `INSERT OR IGNORE` on the `url` UNIQUE constraint (`sqlite3.IntegrityError` → return False)
- Dates stored as ISO strings, parsed by slicing `published[:10]` for `YYYY-MM-DD`

## Database

SQLite at `data/hn_intel.db` (gitignored). Three tables: `blogs` (keyed by `feed_url` UNIQUE), `posts` (keyed by `url` UNIQUE, `blog_id` FK), `citations` (`source_blog_id` → `target_blog_id`). WAL mode + foreign keys enabled. Schema in `db.init_db()`.

## Test Patterns

All tests create in-memory DBs with a `_mem_db()` helper:
```python
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")
init_db(conn)
```
Tests seed data with `upsert_blogs()` + `insert_post()`. HTTP calls in `test_fetcher.py` are mocked. CLI tests use `click.testing.CliRunner`.

## TF-IDF Configuration

Both `analyzer.py` and `clusters.py` use the same vectorizer pattern:
- `token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b"` (3+ chars, must start with letter)
- `min_df=min(3, len(documents))` (adaptive for small corpora)
- `ngram_range=(1, 2)`, `max_df=0.7`, `stop_words="english"`

## Pain Signal Scoring (ideas.py)

Composite score weights: trend momentum (0.35), authority/PageRank (0.25), breadth across blogs (0.25), recency (0.15). Six signal types: wish, frustration, gap, difficulty, broken, opportunity. Signals are clustered via `AgglomerativeClustering` on TF-IDF vectors with cosine distance.

## Gotchas

- `data/` and `output/` are gitignored; only `docs/hn-blogs.opml` is versioned input
- K-means will fail if `n_clusters` > number of blogs with posts
- Citation graph is typically sparse (depends on blogs linking to each other)
- `generate_ideas()` internally calls `compute_trends()`, `extract_citations()`, `build_citation_graph()`, and `compute_centrality()` — it runs a full sub-pipeline
- The `report` command also calls `generate_ideas()` separately, so ideas analysis runs as part of report generation
