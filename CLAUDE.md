# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable mode with dev deps)
pip install -e ".[dev]"

# CLI (entry point: hn_intel.cli:main)
hn-intel fetch                # Fetch RSS feeds → SQLite
hn-intel status               # Show DB stats
hn-intel ideas                # Surface project ideas from pain signals
hn-intel ideas --output-dir output  # Save ideas.md + ideas.json

# Testing (120 tests, all use in-memory SQLite)
python -m pytest tests/ -v
python -m pytest tests/test_ideas.py -v                    # Single file
python -m pytest tests/test_ideas.py::test_extract_pain_signals -v  # Single test
```

## Architecture

Python CLI tool that mines 92 HN popular blog RSS feeds for project ideas based on developer pain signals.

**Data flow**: `opml_parser` → `fetcher` (stores to DB) → `ideas.py` (extracts pain signals, scores, clusters into ideas; internally uses `analyzer`, `network` for trend/authority data) → `reports.py` writes ideas.md + ideas.json to `output/`.

**Key design decisions**:
- All analysis modules receive a `sqlite3.Connection` and call `get_all_posts(conn)` which returns `sqlite3.Row` objects (dict-like access: `row["title"]`)
- `description` field stores **raw HTML** (needed for citation link extraction in `network.py`). Always call `strip_html()` before text analysis.
- `strip_html()` is intentionally duplicated in `analyzer.py`, `clusters.py`, and `ideas.py` (each has its own copy)
- CLI uses **lazy imports** inside command functions to avoid loading sklearn/networkx at startup
- Every CLI command opens/closes its own DB connection via `get_connection()` + `init_db(conn)`
- Post deduplication uses `INSERT OR IGNORE` on the `url` UNIQUE constraint (`sqlite3.IntegrityError` → return False)
- Dates stored as ISO strings, parsed by slicing `published[:10]` for `YYYY-MM-DD`

## Database

SQLite at `data/hn_intel.db` (gitignored). Three tables: `blogs` (keyed by `feed_url` UNIQUE, also has `last_fetched`, `fetch_status`), `posts` (keyed by `url` UNIQUE, `blog_id` FK), `citations` (`source_post_id`, `source_blog_id` → `target_blog_id`, `target_url`). WAL mode + foreign keys enabled. Schema in `db.init_db()`.

## Test Patterns

All tests create in-memory DBs with a `_mem_db()` helper:
```python
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys=ON")
init_db(conn)
```
Tests seed data with `upsert_blogs()` + `insert_post()`. HTTP calls in `test_fetcher.py` are mocked. CLI tests use `click.testing.CliRunner`. Test fixtures use relative dates (`date.today() - timedelta(days=60)`) to avoid expiring past the 12-month date filter.

## Ideas Pipeline (ideas.py)

The core feature. `generate_ideas()` orchestrates the full pipeline:

1. **Extract pain signals** — regex scan for 6 types (wish, frustration, gap, difficulty, broken, opportunity). Date filter skips posts older than `max_age_days` (default 365). Deduplicates by `(post_url, signal_type)` keeping longest match.

2. **TF-IDF vectorize** — title-weighted documents (`"{title} {title} {signal_text}"`). Stop words: sklearn English + `_PAIN_STOP_WORDS` (120+ pain-trigger terms).

3. **Score signals** — composite: trend momentum (0.35) + authority/PageRank (0.25) + breadth (0.25) + recency (0.15). Internally calls `compute_trends()`, `extract_citations()`, `build_citation_graph()`, `compute_centrality()`.

4. **Cluster** — `AgglomerativeClustering` at cosine similarity threshold 0.5. After clustering: breadth updated, scores recomputed, ideas sorted.

5. **Label** — `_extract_title_keywords()` from post titles (2+ title overlap = theme words). `_LABEL_TEMPLATES`: wish→"Better {}", frustration→"Improved {}", gap→"{} Solution", difficulty→"Simplified {}", broken→"Reliable {}", opportunity→"{} Platform".

6. **Filter & renumber** — remove ideas with `blog_count < 2`, renumber `idea_id` sequentially.

## Report Rendering (reports.py)

`generate_ideas_report()` groups evidence sources by `post_url` via `_group_sources_by_post()` so the same post appears once with multiple pain signals as nested bullet points.

## Gotchas

- `data/` and `output/` are gitignored; only `docs/hn-blogs.opml` is versioned input
- `generate_ideas()` internally runs a full sub-pipeline (trends, citations, PageRank)
- Citation graph is typically sparse (depends on blogs linking to each other)
- K-means in `clusters.py` will fail if `n_clusters` > number of blogs with posts
