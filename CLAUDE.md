# CLAUDE.md

This file provides comprehensive guidance for Claude Code (AI assistant) when working with the HN Blog Intelligence Platform codebase.

---

## Project Overview

**HN Blog Intelligence Platform** is a Python CLI tool that analyzes 92 Hacker News popular blog RSS feeds. It:
- Fetches RSS feeds and stores them in SQLite
- Analyzes content using TF-IDF to identify trends and emerging topics
- Builds citation networks between blogs using NetworkX
- Clusters similar blogs based on content similarity
- Surfaces high-impact project ideas from blog pain signals (wishes, frustrations, gaps, difficulties)
- Generates comprehensive reports in Markdown and JSON formats

**Core Technologies**: Python 3.10+, SQLite, scikit-learn, NetworkX, feedparser, Click

---

## Quick Commands

```bash
# Installation
pip install -e ".[dev]"       # Install in editable mode with dev dependencies

# Main workflows
hn-intel fetch                # Fetch RSS feeds and store in SQLite
hn-intel status               # Show database statistics
hn-intel analyze              # Run full analysis pipeline (trends, citations, clusters)
hn-intel ideas                # Surface project ideas from blog pain signals
hn-intel report               # Generate reports to output/ directory

# Testing
python -m pytest tests/ -v    # Run all 97 tests with verbose output

# CLI options
hn-intel fetch --opml docs/hn-blogs.opml --timeout 30 --delay 0.5
hn-intel analyze --max-features 500 --n-clusters 8 --period month
hn-intel ideas --top-n 20 --output-dir output
hn-intel report --output-dir output --max-features 500 --n-clusters 8
```

---

## Project Structure

```
C:\Users\simon\Downloads\hn_popular_blogs_bestpartnerstv\
│
├── hn_intel/                 # Main package
│   ├── __init__.py           # Empty package initializer
│   ├── cli.py                # Click CLI with 5 commands (fetch, status, analyze, ideas, report)
│   ├── opml_parser.py        # Parse OPML XML to extract feed URLs
│   ├── db.py                 # SQLite connection, schema, and query helpers
│   ├── fetcher.py            # RSS feed fetching with requests + feedparser
│   ├── analyzer.py           # TF-IDF keyword extraction and trend detection
│   ├── ideas.py              # Pain signal extraction, scoring, and project idea generation
│   ├── network.py            # Citation extraction and NetworkX graph analysis
│   ├── clusters.py           # Blog clustering using K-means
│   └── reports.py            # Report generation (Markdown + JSON, including ideas)
│
├── tests/                    # Test suite (97 tests)
│   ├── __init__.py
│   ├── test_opml_parser.py
│   ├── test_db.py
│   ├── test_fetcher.py
│   ├── test_analyzer.py
│   ├── test_ideas.py
│   ├── test_network.py
│   ├── test_clusters.py
│   └── test_reports.py
│
├── docs/
│   └── hn-blogs.opml         # 92 HN popular blog RSS feeds (input data)
│
├── data/                     # SQLite database (gitignored)
│   └── hn_intel.db           # Created on first run
│
├── output/                   # Generated reports (gitignored)
│   ├── summary.md
│   ├── trends.md / trends.json
│   ├── network.md / network.json
│   ├── clusters.md / clusters.json
│   └── ideas.md / ideas.json
│
└── pyproject.toml            # Python packaging configuration
```

---

## Architecture & Data Flow

```
Input: docs/hn-blogs.opml (92 feed URLs)
  ↓
opml_parser.parse_opml() → list[dict] with {name, feed_url, site_url}
  ↓
fetcher.fetch_all_feeds() → requests + feedparser → SQLite (blogs + posts tables)
  ↓
SQLite DB (3 tables: blogs, posts, citations)
  ↓
analyzer.compute_trends() → TF-IDF trends by month/week
network.extract_citations() → Parse HTML links → citations table
clusters.compute_blog_vectors() → TF-IDF vectors → K-means clustering
ideas.generate_ideas() → Pain signals → scored & clustered project ideas
  ↓
reports.generate_all_reports() → Markdown + JSON files in output/
```

**Key insight**: All analysis modules read from SQLite using `db.get_all_posts()` and work with `sqlite3.Row` objects (dict-like access).

---

## Database Schema

The SQLite database (`data/hn_intel.db`) has 3 tables:

### Table: `blogs`
```sql
CREATE TABLE blogs (
    id INTEGER PRIMARY KEY,
    name TEXT,                   -- Blog display name
    feed_url TEXT UNIQUE,        -- RSS feed URL (unique constraint)
    site_url TEXT,               -- Blog home page URL
    last_fetched TEXT,           -- ISO timestamp of last fetch
    fetch_status TEXT            -- 'ok' or error message
);
```

### Table: `posts`
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    blog_id INTEGER REFERENCES blogs(id),
    title TEXT,
    description TEXT,            -- Raw HTML (preserved for citation extraction)
    url TEXT UNIQUE,             -- Post URL (unique constraint, deduplication)
    published TEXT,              -- ISO date string (e.g., '2024-01-15T10:00:00')
    author TEXT
);

-- Indexes for performance
CREATE INDEX idx_posts_blog_id ON posts(blog_id);
CREATE INDEX idx_posts_published ON posts(published);
```

### Table: `citations`
```sql
CREATE TABLE citations (
    id INTEGER PRIMARY KEY,
    source_post_id INTEGER REFERENCES posts(id),
    source_blog_id INTEGER REFERENCES blogs(id),  -- Blog that cited
    target_blog_id INTEGER REFERENCES blogs(id),  -- Blog being cited
    target_url TEXT                                -- Full URL cited
);

-- Indexes for network analysis
CREATE INDEX idx_citations_source_blog_id ON citations(source_blog_id);
CREATE INDEX idx_citations_target_blog_id ON citations(target_blog_id);
```

**Important**:
- Foreign keys are enabled (`PRAGMA foreign_keys=ON`)
- WAL mode is enabled for better concurrency (`PRAGMA journal_mode=WAL`)
- `sqlite3.Row` factory is set for dict-like access to query results

---

## Key Conventions & Patterns

### Database Access
```python
# Standard pattern in all modules
from hn_intel.db import get_connection, init_db

conn = get_connection()          # Creates data/ dir, returns Row-factory connection
init_db(conn)                    # Idempotent: CREATE IF NOT EXISTS tables
# ... perform operations ...
conn.close()

# Query pattern
rows = conn.execute("SELECT * FROM posts").fetchall()
for row in rows:
    print(row["title"])          # Dict-like access thanks to sqlite3.Row
```

### HTML Processing
```python
# Three identical strip_html() / _strip_html() implementations exist in:
# - analyzer.py
# - clusters.py
# - ideas.py

def strip_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)  # Decode &amp;, &lt;, etc.
    return text.strip()

# Usage
clean_text = strip_html(post["description"])
```

**Note**: `description` field stores raw HTML to preserve links for citation extraction. Always strip HTML before text analysis.

### TF-IDF Configuration
```python
# Standard pattern in analyzer.py and clusters.py
vectorizer = TfidfVectorizer(
    max_features=500,                           # Top N features
    stop_words="english",                       # Remove common English words
    min_df=min(3, len(documents)),              # Min document frequency (adaptive)
    max_df=0.7,                                  # Max document frequency (70%)
    ngram_range=(1, 2),                         # Unigrams and bigrams
    token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b"  # 3+ chars, start with letter
)
```

**Key insight**: `token_pattern` filters out noise (single chars, numbers, punctuation). Requires tokens to start with a letter and be 3+ characters.

### CLI Lazy Imports
```python
# Pattern in cli.py: imports inside command functions
@main.command()
def analyze(...):
    """Lazy import to avoid side effects at module load time."""
    from hn_intel.analyzer import compute_trends
    from hn_intel.network import build_citation_graph
    # ... use imports ...
```

**Why**: Avoids importing heavy dependencies (sklearn, networkx) unless command is actually invoked.

### Error Handling: Deduplication
```python
# fetcher.py: INSERT OR IGNORE on duplicate URLs
def insert_post(conn, blog_id, entry):
    try:
        conn.execute(
            "INSERT INTO posts (blog_id, title, description, url, ...) VALUES (...)",
            (...)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Duplicate URL, not an error
```

### Date Parsing
```python
# analyzer.py: _period_key()
# Handles ISO dates like '2024-01-15' or '2024-01-15T10:00:00'
date_str = published[:10]  # Extract YYYY-MM-DD
parts = date_str.split("-")
year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

# Convert to period key
if period == "week":
    iso_year, iso_week, _ = date(year, month, day).isocalendar()
    return f"{iso_year}-W{iso_week:02d}"  # e.g., "2024-W03"
else:
    return f"{year}-{month:02d}"  # e.g., "2024-01"
```

---

## Module Reference

### `cli.py` - Command-Line Interface
**Commands**:
- `fetch`: Parse OPML, fetch feeds, store in DB
- `status`: Show DB statistics (blog count, post count, last fetch time)
- `analyze`: Run full analysis pipeline, print summary
- `ideas`: Surface project ideas from blog pain signals (optional `--output-dir` for reports)
- `report`: Run analysis, generate ideas, and generate all reports to output/

**Pattern**: All commands call `get_connection()` and `init_db(conn)` first.

### `opml_parser.py` - OPML Feed Parser
**Main function**: `parse_opml(path) -> list[dict]`
- Parses XML outline elements
- Returns `[{"name": str, "feed_url": str, "site_url": str}, ...]`

### `db.py` - Database Layer
**Key functions**:
- `get_connection(db_path="data/hn_intel.db")` - Returns Row-factory connection
- `init_db(conn)` - Create tables and indexes (idempotent)
- `upsert_blogs(conn, blogs)` - INSERT OR IGNORE blogs by feed_url
- `insert_post(conn, blog_id, entry)` - Returns True/False (False if duplicate URL)
- `get_all_posts(conn)` - JOIN posts with blogs, returns list of Row objects
- `get_blog_domains(conn)` - Returns dict mapping domain strings to blog IDs
- `get_blogs(conn)` - Returns all blogs

**Note**: Always creates parent directory (`data/`) if it doesn't exist.

### `fetcher.py` - RSS Feed Fetcher
**Main function**: `fetch_all_feeds(conn, opml_path, timeout, delay)`
- Parses OPML to get feed URLs
- Upserts blogs to DB
- Fetches each feed with requests + feedparser
- Shows progress bar with tqdm
- Updates `last_fetched` and `fetch_status` fields
- Returns summary dict: `{feeds_ok, feeds_err, new_posts, skipped}`

**Deduplication**: Uses `INSERT OR IGNORE` on post URL (unique constraint).

### `analyzer.py` - TF-IDF Trend Analysis
**Main functions**:
- `extract_keywords(conn, max_features=500)` - Returns (vectorizer, tfidf_matrix, post_ids)
- `compute_trends(conn, period="month")` - Returns dict of {period_key: {keyword: score}}
- `detect_emerging_topics(trends, window=3)` - Returns list of emerging topics (acceleration > 2.0x)
- `find_leading_blogs(conn, keyword)` - Returns blogs that mentioned keyword earliest

**Period keys**: `"2024-01"` for month, `"2024-W03"` for week.

**Trend normalization**: TF-IDF scores are summed per period, then divided by post count.

### `network.py` - Citation Network Analysis
**Main functions**:
- `extract_citations(conn)` - Parse all post descriptions for HTML links, store in citations table
- `build_citation_graph(conn)` - Build NetworkX DiGraph from citations table (blog-level)
- `compute_centrality(graph)` - Calculate PageRank, in-degree, out-degree for each node

**Citation extraction logic**:
1. Parse HTML description for `<a href="...">` tags
2. Extract domain from URL
3. Match domain to blog ID using `get_blog_domains()`
4. Store citation in DB if target blog found

### `clusters.py` - Blog Clustering
**Main functions**:
- `compute_blog_vectors(conn, max_features=500)` - TF-IDF vectors per blog (aggregate all posts)
- `cluster_blogs(blog_vectors, blog_names, vectorizer, n_clusters=8)` - K-means clustering
- `compute_similarity_matrix(blog_vectors)` - Cosine similarity matrix (n_blogs × n_blogs)

**Returns**: List of dicts with cluster assignments, keywords, and member blogs.

### `ideas.py` - Project Idea Generation
**Main functions**:
- `extract_pain_signals(conn)` - Scan all posts for pain-point language (wishes, frustrations, gaps, difficulties, broken, opportunity)
- `extract_signal_keywords(signals, max_features=200)` - TF-IDF on signal texts for clustering
- `score_ideas(signals, emerging, centrality)` - Composite impact scoring (trend 0.35, authority 0.25, breadth 0.25, recency 0.15)
- `build_justification(idea)` - Generate written justification for a project idea
- `cluster_signals(signals, vectorizer, matrix)` - Group related signals into idea themes using agglomerative clustering
- `generate_ideas(conn, max_features, period, top_n)` - Orchestrate full ideas pipeline

**Pain signal types**: wish, frustration, gap, difficulty, broken, opportunity

**Scoring weights**: trend momentum (0.35), authority/PageRank (0.25), breadth across blogs (0.25), recency (0.15)

**Returns**: List of idea dicts with: idea_id, label, impact_score, justification, keywords, signal_count, blog_count, pain_type_breakdown, representative_quote, sources.

### `reports.py` - Report Generation
**Main function**: `generate_all_reports(...)` - Writes up to 9 files to output_dir:
1. `summary.md` - High-level summary including top project ideas
2. `trends.md` / `trends.json` - Keyword trends over time
3. `network.md` / `network.json` - PageRank, top citing/cited blogs
4. `clusters.md` / `clusters.json` - Cluster assignments with keywords
5. `ideas.md` / `ideas.json` - Ranked project ideas with justifications and sources

**Additional function**: `generate_ideas_report(ideas, output_dir)` - Standalone ideas report generation

**Pattern**: Creates output directory if it doesn't exist (`os.makedirs(output_dir, exist_ok=True)`).

---

## Testing

All tests use **in-memory SQLite** (`:memory:`) for isolation. No fixtures or data files on disk.

### Test Structure
Each module has a corresponding test file:
- `test_opml_parser.py` - Tests OPML parsing with sample XML
- `test_db.py` - Tests database schema and query helpers
- `test_fetcher.py` - Mocks HTTP requests to test feed fetching
- `test_analyzer.py` - Tests TF-IDF and trend detection
- `test_ideas.py` - Tests pain signal extraction, scoring, clustering, idea generation, CLI integration
- `test_network.py` - Tests citation extraction and PageRank
- `test_clusters.py` - Tests blog clustering
- `test_reports.py` - Tests report generation

### Running Tests
```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_analyzer.py -v

# Run specific test function
python -m pytest tests/test_analyzer.py::test_compute_trends -v
```

**Test count**: 97 tests total (as of last check).

---

## Common Tasks

### Adding a New CLI Command
1. Add command function to `cli.py` with `@main.command()` decorator
2. Use lazy imports inside the function
3. Call `get_connection()` and `init_db(conn)` first
4. Close connection at the end
5. Use `click.echo()` for output

### Adding a New Analysis Module
1. Create new file in `hn_intel/`
2. Import `from hn_intel.db import get_connection, init_db, get_all_posts`
3. Process posts using `sqlite3.Row` dict-like access
4. Follow TF-IDF pattern if doing text analysis
5. Create corresponding test file in `tests/`

### Modifying Database Schema
1. Update `init_db()` in `db.py` with new tables/columns
2. Consider adding indexes for query performance
3. Update all query functions that depend on schema
4. Add migration logic if needed (currently no migrations)
5. Update CLAUDE.md database schema section

### Adding a New Report Type
1. Add function to `reports.py`
2. Follow pattern: accept analysis results as params, write to output_dir
3. Use `os.path.join()` for cross-platform paths
4. Return file path from function
5. Add to `generate_all_reports()` function

---

## Development Guidelines

### Code Style
- **Functions**: Descriptive docstrings with Args/Returns sections
- **Imports**: Standard library first, then third-party, then local
- **Error handling**: Explicit try/except with meaningful error messages
- **Variables**: Descriptive names (avoid single-letter except loop counters)

### File Paths
- **Absolute paths recommended**: Working directory may change
- **Cross-platform**: Use `os.path.join()` or pathlib
- **Default paths**: `data/hn_intel.db`, `docs/hn-blogs.opml`, `output/`

### Dependencies
**Runtime**:
- feedparser (RSS parsing)
- click (CLI framework)
- scikit-learn (TF-IDF, clustering)
- networkx (graph analysis)
- tabulate (table formatting)
- tqdm (progress bars)
- requests (HTTP)

**Development**:
- pytest (testing)

**Installation**: `pip install -e ".[dev]"` installs both runtime and dev dependencies.

---

## Important Notes

### Data Persistence
- SQLite DB is gitignored (`data/` directory)
- Output reports are gitignored (`output/` directory)
- Only `docs/hn-blogs.opml` is version-controlled

### Performance Considerations
- TF-IDF vectorization can be slow with many posts (thousands+)
- Citation extraction requires parsing all post descriptions
- K-means clustering complexity: O(n_posts × n_features × n_clusters × n_iterations)

### Known Patterns
- `strip_html()` / `_strip_html()` exists in three places (analyzer.py, clusters.py, ideas.py) - intentional duplication
- CLI uses lazy imports to speed up command invocation
- Database connection is opened/closed per CLI command (no persistent connection)
- All dates are stored as ISO strings, not as SQLite DATE type

---

## Troubleshooting

### Common Issues

**Issue**: "No such table: posts"
- **Fix**: Ensure `init_db(conn)` is called before queries

**Issue**: Tests fail with "database is locked"
- **Fix**: Ensure connections are closed in test teardown

**Issue**: Empty trends returned
- **Fix**: Check that posts have valid `published` dates and non-empty descriptions

**Issue**: Citation extraction finds no citations
- **Fix**: Verify post descriptions contain raw HTML (not stripped text)

**Issue**: K-means fails with "n_samples < n_clusters"
- **Fix**: Reduce `n_clusters` or fetch more blog posts

---

## Example Workflows

### Complete Analysis from Scratch
```bash
# 1. Install
pip install -e ".[dev]"

# 2. Fetch feeds (takes 1-2 minutes)
hn-intel fetch

# 3. Check status
hn-intel status

# 4. Run analysis and generate reports
hn-intel report

# 5. View reports
cat output/trends.md
cat output/citation_network.md
cat output/blog_clusters.md
cat output/ideas.md
```

### Development Workflow
```bash
# 1. Make code changes
# 2. Run tests
python -m pytest tests/ -v

# 3. Test CLI command
hn-intel status

# 4. Verify output
hn-intel analyze
```

---

## References

- **OPML spec**: http://opml.org/spec2.opml
- **RSS/Atom parsing**: https://feedparser.readthedocs.io/
- **TF-IDF**: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
- **NetworkX**: https://networkx.org/documentation/stable/
- **Click CLI**: https://click.palletsprojects.com/

---

## Questions to Ask Before Making Changes

1. Will this change affect the database schema?
2. Do I need to update tests?
3. Are there existing patterns I should follow?
4. Will this impact performance with large datasets?
5. Should this be a new CLI command or part of an existing one?
6. Do I need to update this CLAUDE.md file?

---

## Version Info

- **Python**: 3.10+
- **Package version**: 0.1.0
- **Test count**: 97 tests
- **Database version**: No migrations yet (schema v1)

---

*This file is maintained as the source of truth for how Claude Code should understand and work with this codebase.*
