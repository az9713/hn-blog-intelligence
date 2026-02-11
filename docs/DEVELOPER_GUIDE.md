# Developer Guide

**Architecture and codebase reference for contributors.**

---

## Table of Contents

1. [Setup](#1-setup)
2. [Architecture](#2-architecture)
3. [The Ideas Pipeline](#3-the-ideas-pipeline)
4. [Database Schema](#4-database-schema)
5. [Testing](#5-testing)
6. [Code Conventions](#6-code-conventions)
7. [Dependencies](#7-dependencies)

---

## 1. Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux
pip install -e ".[dev]"
python -m pytest tests/ -v      # Verify: 120 tests pass
```

The project uses `pyproject.toml` for build configuration. `pip install -e ".[dev]"` installs in editable mode with test dependencies. The `hn-intel` CLI command is registered via the `[project.scripts]` entry point.

---

## 2. Architecture

### Data Flow

```
docs/hn-blogs.opml (92 RSS feed URLs)
        │
        ▼
┌──────────────────┐
│  opml_parser.py  │  Parse OPML XML → list of feed URLs
└────────┬─────────┘
         ▼
┌──────────────────┐
│   fetcher.py     │  HTTP fetch → RSS parse → store in SQLite
└────────┬─────────┘
         ▼
┌──────────────────┐
│   data/          │  SQLite database: blogs, posts, citations tables
│   hn_intel.db    │
└────────┬─────────┘
         ▼
┌──────────────────┐
│   ideas.py       │  Pain signal extraction → scoring → clustering → ideas
│                  │  (internally calls analyzer.py, network.py)
└────────┬─────────┘
         ▼
┌──────────────────┐
│   reports.py     │  Render ideas.md + ideas.json
└──────────────────┘
```

### Module Roles

| Module | Purpose |
|--------|---------|
| `opml_parser.py` | Parse OPML XML to extract RSS feed URLs |
| `fetcher.py` | Download RSS feeds, parse entries, store in DB |
| `db.py` | SQLite schema, connection management, queries |
| `ideas.py` | **Core pipeline**: pain signal extraction, TF-IDF, scoring, clustering, label generation |
| `analyzer.py` | TF-IDF trend analysis — used internally by `ideas.py` for trend momentum scoring |
| `network.py` | Citation extraction and PageRank — used internally by `ideas.py` for authority scoring |
| `clusters.py` | K-means blog clustering — used by `report` command but not by the ideas pipeline |
| `reports.py` | Markdown + JSON report generation |
| `cli.py` | Click-based CLI with commands: `fetch`, `status`, `analyze`, `ideas`, `report` |

**Key point**: `ideas.py:generate_ideas()` orchestrates a full sub-pipeline. It calls `analyzer.compute_trends()`, `network.extract_citations()`, `network.build_citation_graph()`, and `network.compute_centrality()` internally to get trend and authority data for scoring.

---

## 3. The Ideas Pipeline

This is the core feature. See [IDEAS_PIPELINE_DEEP_DIVE.md](IDEAS_PIPELINE_DEEP_DIVE.md) for a full end-to-end trace with real data.

### 3.1 Pain Signal Extraction

`extract_pain_signals(conn, max_age_days=365)` — scans all posts for six regex pattern families (wish, frustration, gap, difficulty, broken, opportunity).

Key behaviors:
- Strips HTML from `description` field before scanning (raw HTML is stored for citation extraction)
- Prepends title to description: `full_text = title + ". " + stripped_description`
- Extracts surrounding sentence via `_extract_sentence()` and context via `_extract_context()`
- **Date filter**: skips posts older than `max_age_days` (default 365). Posts with missing dates are kept.
- **Deduplication**: by `(post_url, signal_type)`, keeping only the longest match per pair

### 3.2 TF-IDF Vectorization

`extract_signal_keywords(signals, max_features=200)` — builds TF-IDF matrix from signal documents.

Each signal's document: `"{title} {title} {signal_text}"` (title repeated 2x for topic weighting).

Stop words: sklearn's English stop words + `_PAIN_STOP_WORDS` (~120 pain-trigger and filler terms). This prevents signals from clustering by pain language rather than domain topic.

Vectorizer config: `max_features=200`, `min_df=min(2, len(documents))`, `max_df=0.8`, `ngram_range=(1,2)`.

### 3.3 Scoring

`score_ideas(signals, emerging, centrality)` — scores each signal on four dimensions:

| Dimension | Weight | Source |
|-----------|--------|--------|
| Trend momentum | 0.35 | `analyzer.detect_emerging_topics()` — keyword acceleration |
| Authority | 0.25 | `network.compute_centrality()` — PageRank of source blog |
| Breadth | 0.25 | Set after clustering — `cluster_blog_count / total_signaling_blogs` |
| Recency | 0.15 | `e^(-days_ago / 365)` exponential decay |

### 3.4 Clustering

`cluster_signals(signals, ...)` — groups signals using `AgglomerativeClustering`:
- Distance metric: `1 - cosine_similarity` on the TF-IDF matrix
- Threshold: 0.5 (signals need ~50% vocabulary overlap to cluster)
- After clustering: breadth scores are filled in, impact scores recomputed, ideas sorted by max signal score

### 3.5 Label Generation

`_extract_title_keywords()` — extracts keywords from post titles (not signal text):
1. **Tier 1**: words appearing in 2+ titles within the cluster (theme words)
2. **Tier 2**: fallback to highest-impact signal's title keywords
3. Keywords filtered against TF-IDF vocabulary to remove rare proper nouns

`_generate_label()` — applies template based on dominant pain type:
- wish → "Better {}", frustration → "Improved {}", gap → "{} Solution"
- difficulty → "Simplified {}", broken → "Reliable {}", opportunity → "{} Platform"

### 3.6 Quality Filtering and Renumbering

After clustering, `generate_ideas()`:
1. Filters out ideas with `blog_count < 2` (when multi-blog ideas exist)
2. Renumbers `idea_id` sequentially to eliminate gaps from filtering

---

## 4. Database Schema

SQLite at `data/hn_intel.db`. WAL mode + foreign keys enabled. Schema defined in `db.init_db()`.

### Tables

**blogs**
| Column | Type | Constraint |
|--------|------|------------|
| id | INTEGER | PRIMARY KEY |
| name | TEXT | |
| feed_url | TEXT | UNIQUE |
| site_url | TEXT | |
| last_fetched | TEXT | |
| fetch_status | TEXT | |

**posts**
| Column | Type | Constraint |
|--------|------|------------|
| id | INTEGER | PRIMARY KEY |
| blog_id | INTEGER | FK → blogs.id |
| title | TEXT | |
| description | TEXT | Raw HTML |
| url | TEXT | UNIQUE |
| published | TEXT | ISO date string |
| author | TEXT | |

**citations**
| Column | Type | Constraint |
|--------|------|------------|
| id | INTEGER | PRIMARY KEY |
| source_post_id | INTEGER | FK → posts.id |
| source_blog_id | INTEGER | FK → blogs.id |
| target_blog_id | INTEGER | FK → blogs.id |
| target_url | TEXT | |

### Key design decisions

- `description` stores **raw HTML** (needed by `network.py` for citation link extraction). Always call `strip_html()` before text analysis.
- Post deduplication: `INSERT OR IGNORE` on `url` UNIQUE constraint.
- Dates stored as ISO strings, parsed by slicing `published[:10]` for `YYYY-MM-DD`.
- All analysis modules receive a `sqlite3.Connection` and call `db.get_all_posts(conn)` which returns `sqlite3.Row` objects (dict-like access: `row["title"]`).

---

## 5. Testing

120 tests across 8 files. All use in-memory SQLite databases.

### Test helper pattern

```python
def _mem_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_db(conn)
    return conn
```

Tests seed data with `upsert_blogs()` + `insert_post()`. HTTP calls in `test_fetcher.py` are mocked. CLI tests use `click.testing.CliRunner`.

### Running tests

```bash
python -m pytest tests/ -v                                       # All tests
python -m pytest tests/test_ideas.py -v                          # Single file
python -m pytest tests/test_ideas.py::test_extract_pain_signals -v  # Single test
python -m pytest tests/ --cov=hn_intel --cov-report=html         # With coverage
```

### Test files

| File | Focus |
|------|-------|
| `test_ideas.py` | Pain signal extraction, scoring, clustering, label generation, report consolidation, date filtering, deduplication |
| `test_analyzer.py` | TF-IDF vectorization, trend computation, emerging topic detection |
| `test_network.py` | URL extraction, citation graphs, PageRank computation |
| `test_clusters.py` | K-means clustering, similarity matrices |
| `test_db.py` | Database schema, insertion, uniqueness constraints |
| `test_fetcher.py` | RSS parsing, feed fetching, error handling |
| `test_opml_parser.py` | OPML parsing, malformed input handling |
| `test_reports.py` | Report generation, file I/O, Markdown formatting |

### Test date convention

Test fixtures use relative dates (`date.today() - timedelta(days=60)`) instead of hardcoded dates. This prevents tests from breaking as time passes and the 12-month date filter excludes old fixtures.

---

## 6. Code Conventions

- **Lazy imports**: CLI command functions import analysis modules inside the function body to avoid loading sklearn/networkx at startup.
- **`strip_html()` duplication**: Intentionally duplicated in `analyzer.py`, `clusters.py`, and `ideas.py` (each has its own copy). This avoids cross-module dependencies for a simple utility.
- **DB connection management**: Every CLI command opens/closes its own connection via `get_connection()` + `init_db(conn)`.
- **`sqlite3.Row` factory**: All modules rely on dict-like row access (`row["title"]`) via `conn.row_factory = sqlite3.Row`.

---

## 7. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| feedparser | 6.x | RSS/Atom feed parsing |
| click | 8.x | CLI framework |
| scikit-learn | 1.3+ | TF-IDF vectorization, agglomerative clustering, K-means |
| networkx | 3.x | Citation graph, PageRank computation |
| tabulate | 0.9+ | Markdown table formatting in reports |
| tqdm | 4.65+ | Progress bars for feed fetching |
| requests | 2.31+ | HTTP requests for feed fetching |
| pytest | 7+ | Testing (dev dependency) |
