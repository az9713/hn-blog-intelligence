# HN Blog Intelligence Platform - Developer Guide

**Target Audience**: Developers with C/C++/Java backgrounds who are new to Python, pip, virtual environments, SQLite in Python, scikit-learn, networkx, Click CLI, and pytest.

**Goal**: Read only this document and be productive on day one.

---

## Table of Contents

1. [Development Environment Setup](#1-development-environment-setup)
2. [Architecture Deep Dive](#2-architecture-deep-dive)
3. [Database Schema Reference](#3-database-schema-reference)
4. [Testing Guide](#4-testing-guide)
5. [Adding New Features](#5-adding-new-features)
6. [Code Conventions](#6-code-conventions)
7. [Dependency Reference](#7-dependency-reference)
8. [Glossary](#8-glossary)

---

## 1. Development Environment Setup

### 1.1 Python Installation Verification

Python 3.10 or higher is required. Think of Python like the JVM but without separate compilation steps.

```bash
# Check your Python version
python --version
# or
python3 --version

# You should see: Python 3.10.x or higher
```

**Windows users**: Use `python` in your commands.
**Mac/Linux users**: May need to use `python3` if `python` points to Python 2.x.

---

### 1.2 Virtual Environments (like a project-local classpath in Java)

In Java, each project has its own JAR dependencies in a local `lib/` directory or managed by Maven/Gradle. In Python, **virtual environments** provide the same isolation.

**Why virtual environments?**
- **Isolation**: Dependencies for this project don't conflict with system-wide Python packages or other projects.
- **Reproducibility**: Everyone on the team uses the same package versions.
- **No admin rights needed**: Install packages without `sudo`.

**Think of it as**: Creating a project-specific JDK + classpath that lives in your project directory.

**Create and activate a virtual environment**:

```bash
# Navigate to project root
cd C:\Users\simon\Downloads\hn_popular_blogs_bestpartnerstv

# Create virtual environment (one-time setup)
python -m venv venv

# Activate it (must do every time you open a new terminal)
# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

# You'll see (venv) in your prompt when active
```

**Deactivate** (when you're done working):
```bash
deactivate
```

---

### 1.3 Installing the Project in Editable Mode

In Java, you'd run `mvn install` or `gradle build`. In Python, we use `pip` (Python's package manager).

```bash
# With venv activated:
pip install -e ".[dev]"
```

**What this does**:
- `-e`: **Editable mode** (like Maven's `install` that links to source, not copies). Changes to your `.py` files are immediately reflected.
- `.`: Current directory (contains `pyproject.toml`).
- `[dev]`: Install the `dev` optional dependencies (includes `pytest`).

**Result**:
- Installs all dependencies listed in `pyproject.toml`.
- Creates the `hn-intel` CLI command.
- Links your source code so changes take effect immediately.

---

### 1.4 Understanding `pyproject.toml` (like `pom.xml` or `build.gradle`)

`pyproject.toml` is the modern Python build configuration file. It defines:

**Java Analogy**: `pom.xml` in Maven or `build.gradle` in Gradle.

**Structure**:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
# Like specifying Maven version and build plugins

[project]
name = "hn-intel"                # Artifact ID in Maven
version = "0.1.0"                # Version tag
requires-python = ">=3.10"       # Minimum Python version (like <maven.compiler.target>)

dependencies = [                 # Like <dependencies> in pom.xml
    "feedparser>=6.0,<7.0",
    "click>=8.0,<9.0",
    "scikit-learn>=1.3,<2.0",
    "networkx>=3.0,<4.0",
    "tabulate>=0.9,<1.0",
    "tqdm>=4.65,<5.0",
    "requests>=2.31,<3.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0,<9.0"]       # Like test-scoped dependencies

[project.scripts]
hn-intel = "hn_intel.cli:main"   # Creates CLI command (like creating executable JAR)
# Equivalent to: java -jar hn-intel.jar → runs cli.main()
```

**Key Concepts**:
- **Version constraints**: `>=6.0,<7.0` means "version 6.x only" (like Maven's `[6.0,7.0)`)
- **Entry points**: `hn-intel = "hn_intel.cli:main"` creates a command-line executable that calls `hn_intel/cli.py:main()`

---

### 1.5 `requirements.txt` vs `pyproject.toml`

**C++ Analogy**: `requirements.txt` is like a dependency list file; `pyproject.toml` is like CMakeLists.txt with metadata.

| File | Purpose | When to Use |
|------|---------|-------------|
| `pyproject.toml` | **Modern, preferred**. Defines project metadata, dependencies, build config, entry points. | For libraries/applications you distribute. |
| `requirements.txt` | **Legacy**. Simple list of packages with versions. | For quick deployment scripts, legacy projects. |

**This project has both** for compatibility:
- `pyproject.toml`: Source of truth for dependencies.
- `requirements.txt`: Generated/maintained manually for simpler `pip install -r requirements.txt` workflow.

**Best practice**: Use `pyproject.toml` and `pip install -e ".[dev]"` for development.

---

### 1.6 Verification Checklist

After setup, verify everything works:

```bash
# 1. Check CLI is installed
hn-intel --help
# Should show: HN Blog Intelligence Platform

# 2. Check Python can import modules
python -c "from hn_intel import db; print('Import successful')"

# 3. Run tests
python -m pytest tests/ -v

# 4. Check database connection
hn-intel status
# Should show: Blogs: 0, Posts: 0, Last fetch: never
```

---

## 2. Architecture Deep Dive

### 2.1 System Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    CLI Layer (cli.py)                      │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌───────┐ ┌────────┐│
│  │  fetch   │ │ status  │ │ analyze  │ │ ideas │ │ report ││
│  └────┬─────┘ └────┬────┘ └────┬─────┘ └──┬────┘ └───┬────┘│
│       │            │           │           │          │     │
│  ┌────▼─────┐ ┌────▼────┐ ┌───▼───────────▼──────────▼┐    │
│  │ fetcher  │ │   db    │ │  analyzer  network  ideas  │    │
│  │          │ │         │ │  clusters  reports          │    │
│  └────┬─────┘ └────┬────┘ └──────────────┬─────────────┘    │
│       │            │                   │                  │
│  ┌────▼────┐  ┌────▼─────────────────▼────┐              │
│  │  opml   │  │     SQLite Database        │              │
│  │ parser  │  │  (data/hn_intel.db)        │              │
│  └─────────┘  └───────────────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

**Layer Breakdown** (like a typical MVC or n-tier architecture):

1. **CLI Layer**: User commands (like Servlets handling HTTP requests).
2. **Business Logic**: `fetcher`, `analyzer`, `network`, `clusters`, `reports` (like Service layer).
3. **Data Access**: `db.py` (like DAO/Repository pattern).
4. **Data Storage**: SQLite database file (like MySQL database).
5. **Utilities**: `opml_parser.py` (like utility classes).

---

### 2.2 Module: `opml_parser.py`

**Purpose**: Parse OPML XML files to extract RSS feed information.

**What is OPML?**
Outline Processor Markup Language - an XML format for lists of RSS feeds. Think of it as a configuration file listing all blogs to monitor.

**Key Function**:

```python
def parse_opml(path):
    """Parse an OPML file and return a list of feed dicts.

    Args:
        path: Path to the OPML file.

    Returns:
        List of dicts with keys: name, feed_url, site_url.
    """
```

**How it works**:

1. **Uses `xml.etree.ElementTree`**: Python's built-in XML parser (like Java's DOM parser but simpler).
   - **Java equivalent**: `javax.xml.parsers.DocumentBuilder`
   - **C++ equivalent**: libxml2 or TinyXML

2. **Iterates over `<outline>` elements**: Each outline with `type="rss"` is a feed.

3. **Extracts attributes**:
   - `xmlUrl`: RSS feed URL
   - `text` or `title`: Blog name
   - `htmlUrl`: Blog website URL

**Example OPML**:
```xml
<opml version="1.0">
  <body>
    <outline type="rss" text="Joel on Software"
             xmlUrl="https://www.joelonsoftware.com/feed/"
             htmlUrl="https://www.joelonsoftware.com/"/>
    <outline type="rss" text="Paul Graham"
             xmlUrl="http://paulgraham.com/rss.html"
             htmlUrl="http://paulgraham.com/"/>
  </body>
</opml>
```

**Returns**:
```python
[
    {
        "name": "Joel on Software",
        "feed_url": "https://www.joelonsoftware.com/feed/",
        "site_url": "https://www.joelonsoftware.com/"
    },
    {
        "name": "Paul Graham",
        "feed_url": "http://paulgraham.com/rss.html",
        "site_url": "http://paulgraham.com/"
    }
]
```

**Error Handling**: Skips outlines without `xmlUrl`. No exceptions thrown for malformed entries.

---

### 2.3 Module: `db.py`

**Purpose**: SQLite database abstraction layer.

**What is SQLite?**
A serverless, file-based SQL database (like an embedded H2 or Derby database in Java). The entire database is a single `.db` file.

**Key Concept**: `sqlite3` module is **built into Python** (like JDBC but no driver download needed).

---

#### Database Connection Pattern

```python
import sqlite3

def get_connection(db_path="data/hn_intel.db"):
    """Open a SQLite connection, ensuring the parent directory exists.

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row.
    """
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Key line: makes rows dict-like
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
    conn.execute("PRAGMA foreign_keys=ON")   # Enable foreign key constraints
    return conn
```

**Important Concepts**:

1. **`sqlite3.connect(db_path)`**: Opens or creates a database file.
   - **Java equivalent**: `DriverManager.getConnection("jdbc:sqlite:data/hn_intel.db")`

2. **`row_factory = sqlite3.Row`**: By default, rows are tuples (`(1, 'Alice', 'alice@example.com')`). With `Row`, they behave like dicts:
   ```python
   row = cursor.fetchone()
   print(row["name"])      # Dict-like access (preferred)
   print(row[1])           # Tuple-like access (still works)
   ```
   - **Java equivalent**: Using `ResultSet.getString("name")` vs `ResultSet.getString(2)`

3. **`PRAGMA journal_mode=WAL`**: Write-Ahead Logging improves concurrency (readers don't block writers).

4. **`PRAGMA foreign_keys=ON`**: SQLite doesn't enforce foreign keys by default. This enables them.

---

#### Schema Initialization

```python
def init_db(conn):
    """Create tables and indexes if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS blogs (...);
        CREATE TABLE IF NOT EXISTS posts (...);
        CREATE TABLE IF NOT EXISTS citations (...);
        CREATE INDEX IF NOT EXISTS idx_posts_blog_id ON posts(blog_id);
        ...
    """)
```

**`executescript()` vs `execute()`**:
- `execute()`: Runs a single SQL statement.
- `executescript()`: Runs multiple statements separated by semicolons (like running a `.sql` file).

---

#### INSERT OR IGNORE for Deduplication

```python
def upsert_blogs(conn, blogs):
    """Insert blogs, ignoring duplicates by feed_url."""
    conn.executemany(
        "INSERT OR IGNORE INTO blogs (name, feed_url, site_url) VALUES (?, ?, ?)",
        [(b["name"], b["feed_url"], b["site_url"]) for b in blogs],
    )
    conn.commit()
```

**Key Concepts**:

1. **`INSERT OR IGNORE`**: SQLite-specific. If a UNIQUE constraint fails (e.g., `feed_url` already exists), silently skip the insert.
   - **MySQL equivalent**: `INSERT IGNORE`
   - **PostgreSQL equivalent**: `INSERT ... ON CONFLICT DO NOTHING`

2. **`executemany(sql, params_list)`**: Batch insert. Efficient for inserting many rows.
   - **Java equivalent**: `PreparedStatement.addBatch()` + `executeBatch()`

3. **`?` placeholders**: Positional parameters (like `PreparedStatement` in Java).
   - **Protects against SQL injection**.

4. **`conn.commit()`**: SQLite uses transactions by default. You must commit to persist changes.
   - **Java equivalent**: `connection.commit()`

---

#### Key Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `get_connection(db_path)` | Open/create database connection | `sqlite3.Connection` |
| `init_db(conn)` | Create tables/indexes if not exist | None |
| `upsert_blogs(conn, blogs)` | Insert blogs, skip duplicates | None |
| `insert_post(conn, blog_id, entry)` | Insert a post, return False if duplicate URL | `True` if inserted, `False` if duplicate |
| `get_all_posts(conn)` | Fetch all posts with blog name joined | List of `sqlite3.Row` |
| `get_blog_domains(conn)` | Build domain → blog_id mapping | Dict `{domain: blog_id}` |
| `get_blogs(conn)` | Fetch all blogs | List of `sqlite3.Row` |

**Design Pattern**: All functions take `conn` as the first parameter (dependency injection). Never create connections inside modules (keeps functions testable).

---

### 2.4 Module: `fetcher.py`

**Purpose**: Download RSS feeds and store posts in the database.

**Key Dependencies**:
- `requests`: HTTP library (like Apache HttpClient but simpler)
- `feedparser`: RSS/Atom XML parser (like Rome library in Java)
- `tqdm`: Progress bar for terminal (like ProgressBar in Java)

---

#### HTTP Requests with `requests`

```python
import requests

resp = requests.get(feed_url, timeout=timeout)
resp.raise_for_status()  # Raises exception if HTTP error (4xx, 5xx)
content = resp.content   # Bytes
```

**`requests` vs Java**:

| Python | Java Equivalent |
|--------|-----------------|
| `requests.get(url, timeout=30)` | `HttpURLConnection` + `setConnectTimeout()` + `setReadTimeout()` |
| `resp.status_code` | `response.getStatusCode()` |
| `resp.raise_for_status()` | Manually check `if (statusCode >= 400)` |
| `resp.content` | `response.getEntity().getContent()` |

**Much simpler than Java's HttpURLConnection!**

---

#### RSS Parsing with `feedparser`

```python
import feedparser

feed = feedparser.parse(resp.content)

for entry in feed.entries:
    title = entry.get("title", "")
    link = entry.get("link", "")
    summary = entry.get("summary", "")
    published_parsed = entry.get("published_parsed")  # time.struct_time
```

**What `feedparser` does**:
- Parses RSS 2.0, Atom, and other formats into a unified Python dict structure.
- Handles malformed XML gracefully (doesn't throw exceptions for minor errors).
- Normalizes dates into `time.struct_time`.

**Java equivalent**: Rome library or custom SAX/DOM parsing.

---

#### Main Function: `fetch_all_feeds()`

```python
def fetch_all_feeds(conn, opml_path="docs/hn-blogs.opml", timeout=30, delay=0.5):
    """Fetch all feeds from an OPML file and insert posts into the database.

    Returns:
        Dict with summary stats: feeds_ok, feeds_err, new_posts, skipped.
    """
```

**Workflow**:

1. **Parse OPML** → get list of blogs
2. **Initialize database** → create tables
3. **Insert blogs** → upsert to blogs table
4. **For each feed**:
   a. Fetch RSS XML via HTTP
   b. Parse with `feedparser`
   c. Extract entries (posts)
   d. Insert each post into database
   e. Update blog's `last_fetched` and `fetch_status`
   f. Sleep for `delay` seconds (rate limiting)

**Error Handling**:
- **Per-feed try/except**: If one feed fails, continue with others.
- **Stores error message** in `blogs.fetch_status` (truncated to 200 chars).

**Rate Limiting**:
```python
time.sleep(delay)  # 0.5 seconds between feeds (respectful scraping)
```

**Progress Bar**:
```python
from tqdm import tqdm

for blog in tqdm(blogs, desc="Fetching feeds"):
    # Shows: Fetching feeds: 42%|████▎     | 21/50 [00:10<00:14, 2.05it/s]
```

---

### 2.5 Module: `analyzer.py`

**Purpose**: TF-IDF keyword extraction and trend detection.

**What is TF-IDF?**

**TF-IDF = Term Frequency × Inverse Document Frequency**

**Simple explanation**: Finds words that are **important** in a document by being **frequent in that document** but **rare across all documents**.

**Example**:
- Document 1: "Python is great for data science. Python is easy."
- Document 2: "Java is great for enterprise apps. Java is verbose."
- Document 3: "JavaScript is great for web development."

**TF-IDF scores** (simplified):
- "Python" scores high in Doc 1 (frequent in Doc 1, rare in others)
- "great" scores low in all docs (common word, appears in all docs)
- "data" scores high in Doc 1 (appears once but unique to Doc 1)

**Why TF-IDF?**
- Filters out common words ("the", "is", "great") without a stopword list.
- Highlights distinctive terms.

---

#### HTML Stripping

```python
def strip_html(text):
    """Remove HTML tags from text."""
    text = re.sub(r"<[^>]+>", " ", text or "")  # Regex: replace <anything> with space
    text = html.unescape(text)                  # &amp; → &, &lt; → <
    return text.strip()
```

**Why needed?**
RSS feed descriptions often contain HTML: `<p>Check out <a href="...">this link</a>!</p>`

**Regex breakdown**:
- `<[^>]+>`: Match `<`, then any chars except `>`, then `>` (matches any HTML tag).
- **C++ equivalent**: Use regex library (`<regex>`) or custom parser.

---

#### TF-IDF Vectorization

```python
from sklearn.feature_extraction.text import TfidfVectorizer

def extract_keywords(conn, max_features=500):
    """Run TF-IDF on title + stripped description for all posts.

    Returns:
        Tuple of (fitted TfidfVectorizer, tfidf_matrix, list of post IDs).
    """
    posts = get_all_posts(conn)
    documents = []
    post_ids = []

    for post in posts:
        text = (post["title"] or "") + " " + strip_html(post["description"])
        documents.append(text)
        post_ids.append(post["id"])

    vectorizer = TfidfVectorizer(
        max_features=500,           # Keep top 500 words by TF-IDF score
        stop_words="english",       # Remove common English words ("the", "is", "and")
        min_df=3,                   # Word must appear in at least 3 documents
        max_df=0.7,                 # Word must appear in at most 70% of documents
        ngram_range=(1, 2),         # Capture 1-word and 2-word phrases
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b",  # Explained below
    )

    tfidf_matrix = vectorizer.fit_transform(documents)
    return vectorizer, tfidf_matrix, post_ids
```

**Key Parameters Explained**:

| Parameter | Meaning | Why? |
|-----------|---------|------|
| `max_features=500` | Keep top 500 features (words/phrases) | Limit dimensionality (like PCA in ML) |
| `stop_words="english"` | Remove "the", "is", "and", etc. | Focus on meaningful words |
| `min_df=3` | Word must appear in ≥3 documents | Ignore typos and rare words |
| `max_df=0.7` | Word must appear in ≤70% of docs | Ignore overly common words |
| `ngram_range=(1, 2)` | Capture "machine" (1-gram) and "machine learning" (2-gram) | Phrases are more meaningful |
| `token_pattern=...` | See below | Custom word extraction |

**Token Pattern Regex**: `r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b"`

- `(?u)`: Unicode-aware word boundaries
- `\b`: Word boundary
- `[a-zA-Z]`: First char must be a letter (not a digit)
- `[a-zA-Z0-9]{2,}`: Followed by 2+ alphanumeric chars
- **Result**: Extracts "Python", "API", "web2py" but not "123", "a", "42nd"

**TF-IDF Matrix** (sparse matrix):

```
           python  machine  learning  java  api  ...
Post 1     0.523   0.000    0.000     0.0   0.2
Post 2     0.000   0.812    0.743     0.0   0.0
Post 3     0.312   0.000    0.000     0.8   0.0
```

- **Rows**: Posts
- **Columns**: Keywords
- **Values**: TF-IDF scores (0.0 to ~1.0)
- **Sparse**: Most values are 0 (efficient storage)

**Java equivalent**: Apache Lucene's TF-IDF scoring, or custom implementation.

---

#### Trend Computation

```python
def compute_trends(conn, period="month"):
    """Bucket posts by period, sum TF-IDF per keyword per period, normalize by post count.

    Returns:
        Dict of {period_key: {keyword: normalized_score}}.
    """
```

**Algorithm**:

1. **Run TF-IDF** on all posts → get matrix
2. **Group posts by time period** (e.g., "2024-01", "2024-02")
3. **For each period**:
   - Sum TF-IDF scores for each keyword across posts in that period
   - Normalize by number of posts (prevents bias toward high-post periods)
4. **Return**: `{"2024-01": {"python": 0.523, "api": 0.312}, ...}`

**Example output**:
```python
{
    "2024-01": {"python": 0.42, "machine learning": 0.38, "api": 0.25},
    "2024-02": {"python": 0.45, "docker": 0.52, "kubernetes": 0.48},
    "2024-03": {"python": 0.88, "ai": 0.95, "chatgpt": 1.12}
}
```

Notice "ai" and "chatgpt" spike in 2024-03.

---

#### Emerging Topic Detection

```python
def detect_emerging_topics(trends, window=3):
    """Compare recent period to historical average, flag acceleration > 2.0x.

    Returns:
        List of dicts: {keyword, recent_score, historical_avg, acceleration}.
    """
```

**Algorithm**:

1. **Split time periods**:
   - Recent: Last 3 periods (e.g., Mar, Apr, May)
   - Historical: All periods before recent (Jan, Feb)

2. **For each keyword**:
   - `recent_avg = average(scores in recent periods)`
   - `historical_avg = average(scores in historical periods)`
   - `acceleration = recent_avg / historical_avg`

3. **Filter**: Keep keywords where `acceleration > 2.0x` (doubling or more)

4. **Sort** by acceleration descending

**Example**:
```python
[
    {"keyword": "chatgpt", "recent_score": 1.12, "historical_avg": 0.05, "acceleration": 22.4},
    {"keyword": "ai", "recent_score": 0.95, "historical_avg": 0.20, "acceleration": 4.75},
    {"keyword": "kubernetes", "recent_score": 0.48, "historical_avg": 0.22, "acceleration": 2.18}
]
```

"chatgpt" is emerging (22x increase).

---

#### Finding Leading Blogs

```python
def find_leading_blogs(conn, keyword):
    """Find which blogs mentioned a keyword earliest and most frequently.

    Returns:
        List of dicts: {blog_name, first_mention, mention_count}.
    """
```

**Algorithm**:

1. Iterate all posts
2. For each post, check if keyword appears in title or description (case-insensitive)
3. Track per blog:
   - First mention date (earliest published date)
   - Mention count (how many posts mentioned it)
4. Sort by first mention ascending (earliest first)

**Use case**: "Who talked about Rust first?"

---

### 2.6 Module: `network.py`

**Purpose**: Extract cross-blog citations and analyze the citation graph.

**What is a citation?**
When Blog A's post links to Blog B's domain in its description, that's a citation.

---

#### Domain Normalization

```python
def _normalize_domain(domain):
    """Normalize a domain for matching.

    Strips www. prefix and handles shared platforms.
    """
    domain = domain.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain
```

**Why normalize?**
- `www.example.com` and `example.com` should be the same.
- `alice.substack.com` and `bob.substack.com` are **different** (shared platform).

**Shared platforms**:
```python
_SHARED_PLATFORMS = {"blogspot.com", "substack.com", "github.io", "dreamwidth.org"}
```

For these, we keep the full subdomain (e.g., `alice.substack.com` ≠ `bob.substack.com`).

---

#### Citation Extraction with Regex

```python
_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)

urls = _HREF_RE.findall(description)
```

**Regex breakdown**: `href=["\']([^"\']+)["\']`
- `href=`: Literal "href="
- `["\']`: Single or double quote
- `([^"\']+)`: **Capture group** - one or more chars that are not quotes
- `["\']`: Closing quote

**Matches**: `<a href="https://example.com">`, `<a href='http://foo.bar'>`
**Extracts**: `https://example.com`, `http://foo.bar`

**Why not use HTML parser?**
Regex is fast for simple extraction. For complex HTML, use `BeautifulSoup` or `lxml`.

---

#### Citation Graph with NetworkX

```python
import networkx as nx

def build_citation_graph(conn):
    """Build a directed citation graph from the citations table.

    Returns:
        networkx.DiGraph with blog nodes and weighted citation edges.
    """
    graph = nx.DiGraph()  # Directed graph (citations have direction)

    # Add nodes (blogs)
    blogs = get_blogs(conn)
    for blog in blogs:
        graph.add_node(blog["id"], name=blog["name"])

    # Add edges (citations)
    rows = conn.execute(
        "SELECT source_blog_id, target_blog_id, COUNT(*) as weight "
        "FROM citations GROUP BY source_blog_id, target_blog_id"
    ).fetchall()

    for row in rows:
        graph.add_edge(row["source_blog_id"], row["target_blog_id"], weight=row["weight"])

    return graph
```

**What is NetworkX?**
A Python library for graph/network analysis (like JGraphT in Java or Boost Graph Library in C++).

**DiGraph (Directed Graph)**:
- **Nodes**: Blogs
- **Edges**: Citations (Blog A → Blog B)
- **Weights**: Number of citations

**Visualization** (conceptual):
```
    Joel ──(5)──> Paul Graham
      ↓(2)          ↑(3)
   Coding Horror ──┘
```

**Java equivalent**: Adjacency list with `Map<Integer, List<Edge>>`.

---

#### PageRank Centrality

```python
def compute_centrality(graph):
    """Compute centrality metrics for each blog in the citation graph.

    Returns:
        Dict mapping blog name to dict of centrality metrics.
    """
    pagerank = nx.pagerank(graph, weight="weight")
    betweenness = nx.betweenness_centrality(graph, weight="weight")

    result = {}
    for node in graph.nodes():
        name = graph.nodes[node].get("name", str(node))
        result[name] = {
            "pagerank": pagerank.get(node, 0.0),
            "betweenness": betweenness.get(node, 0.0),
            "in_degree": graph.in_degree(node),   # How many cite this blog
            "out_degree": graph.out_degree(node), # How many this blog cites
        }

    return result
```

**Centrality Metrics Explained**:

| Metric | Meaning | High Value Indicates |
|--------|---------|----------------------|
| **PageRank** | Importance based on citations (like Google's algorithm) | Authoritative blog (many important blogs cite it) |
| **Betweenness** | How often a node lies on shortest paths between others | Bridge blog (connects different communities) |
| **In-Degree** | Number of incoming citations | Popular blog (many blogs cite it) |
| **Out-Degree** | Number of outgoing citations | Curator blog (cites many others) |

**PageRank Intuition**:
- If Blog A has high PageRank, citations from Blog A are worth more.
- Like academic citations: a citation from Nature is worth more than from an obscure journal.

**Betweenness Intuition**:
- Blog B connects Python community with Rust community.
- High betweenness → Blog B is a bridge between different topics.

---

### 2.7 Module: `clusters.py`

**Purpose**: Group blogs by content similarity using cosine similarity and K-means clustering.

---

#### Cosine Similarity

**What is cosine similarity?**
Measures the angle between two vectors. Close angle = similar content.

**Formula**: `similarity = cos(θ) = (A · B) / (||A|| × ||B||)`

**Range**: -1 to 1 (for TF-IDF, always 0 to 1)
- **1.0**: Identical content
- **0.5**: Moderately similar
- **0.0**: No overlap

**Visual Analogy** (2D vectors):
```
      A (Python blog)
      ↑
     /|
    / | θ=30° → cos(30°)=0.87 (very similar)
   /  |
  ↙   → B (Machine Learning blog)
```

**Example**:
- Blog A: TF-IDF vector `[0.8 (python), 0.6 (api), 0.0 (rust)]`
- Blog B: TF-IDF vector `[0.7 (python), 0.5 (api), 0.0 (rust)]`
- Cosine similarity: **0.99** (very similar - both focus on Python and APIs)

**Blog C**: TF-IDF vector `[0.0 (python), 0.1 (api), 0.9 (rust)]`
- Similarity between A and C: **0.06** (low - different topics)

---

#### Creating Blog Vectors

```python
def compute_blog_vectors(conn, max_features=500):
    """Concatenate all posts per blog into one document and TF-IDF vectorize.

    Returns:
        Tuple of (tfidf_matrix, blog_names, vectorizer).
    """
    posts = get_all_posts(conn)

    # Group posts by blog
    blog_docs = defaultdict(list)
    for post in posts:
        blog_name = post["blog_name"]
        title = post["title"] or ""
        description = strip_html(post["description"])
        blog_docs[blog_name].append(title + " " + description)

    # Create one document per blog (all posts concatenated)
    blog_names = sorted(blog_docs.keys())
    documents = [" ".join(blog_docs[name]) for name in blog_names]

    # TF-IDF vectorize (one vector per blog)
    vectorizer = TfidfVectorizer(...)
    tfidf_matrix = vectorizer.fit_transform(documents)

    return tfidf_matrix, blog_names, vectorizer
```

**Key insight**: Each blog becomes **one document** (all its posts merged). The TF-IDF matrix has **one row per blog**.

---

#### K-means Clustering

**What is K-means?**
An algorithm that groups items into `k` clusters by minimizing distance to cluster centers (centroids).

**Algorithm**:
1. Choose `k` random centroids
2. Assign each blog to the nearest centroid
3. Recompute centroids as the mean of assigned blogs
4. Repeat 2-3 until convergence

**Java/C++ equivalent**: Implement manually or use Weka (Java) / MLpack (C++).

```python
def cluster_blogs(blog_vectors, blog_names, vectorizer, n_clusters=8):
    """Cluster blogs using K-means on TF-IDF vectors.

    Returns:
        List of cluster dicts with cluster_id, label, and blogs.
    """
    from sklearn.cluster import KMeans

    k = min(n_clusters, len(blog_names))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(blog_vectors)  # labels[i] = cluster ID for blog i

    feature_names = vectorizer.get_feature_names_out()
    clusters = []

    for cluster_id in range(k):
        # Get centroid (average vector for this cluster)
        centroid = km.cluster_centers_[cluster_id]

        # Find top 5 keywords in centroid
        top_indices = np.argsort(centroid)[::-1][:5]
        top_terms = [feature_names[i] for i in top_indices]
        label = ", ".join(top_terms)  # e.g., "python, machine, learning, data, science"

        # Get blogs in this cluster
        member_blogs = [blog_names[i] for i, lbl in enumerate(labels) if lbl == cluster_id]

        clusters.append({
            "cluster_id": cluster_id,
            "label": label,
            "blogs": member_blogs,
        })

    return clusters
```

**Example output**:
```python
[
    {
        "cluster_id": 0,
        "label": "python, machine, learning, data, science",
        "blogs": ["Fast.ai Blog", "PyImageSearch", "Towards Data Science"]
    },
    {
        "cluster_id": 1,
        "label": "rust, systems, performance, memory, safety",
        "blogs": ["Rust Blog", "Without Boats", "Baby Steps"]
    },
    {
        "cluster_id": 2,
        "label": "javascript, web, frontend, react, vue",
        "blogs": ["CSS-Tricks", "Smashing Magazine", "Dev.to"]
    }
]
```

**Centroid**: The "average blog" of a cluster. Top keywords represent the cluster theme.

---

### 2.8 Module: `ideas.py`

**Purpose**: Mine blog content for pain signals and surface high-impact project ideas.

**What is a pain signal?**
When a blogger writes "I wish there was a better tool for..." or "it's frustratingly hard to...", that's a pain signal — an explicit expression of an unmet need. This module detects six categories of pain language using regex patterns.

**Key Dependencies**:
- `scikit-learn`: TF-IDF vectorization and agglomerative clustering
- `hn_intel.analyzer`: Emerging topic detection (for trend scoring)
- `hn_intel.network`: Citation graph (for authority/PageRank scoring)

---

#### Pain Signal Categories

```python
_PAIN_PATTERNS = {
    "wish": re.compile(r"(?:i wish|would be nice|if only|someone should build|...)"),
    "frustration": re.compile(r"(?:frustrat\w*|annoy\w*|pain point|drives me crazy|...)"),
    "gap": re.compile(r"(?:no good (?:way|tool|solution)|missing|lacking|...)"),
    "difficulty": re.compile(r"(?:hard to|difficult to|impossible to|struggle with|...)"),
    "broken": re.compile(r"(?:broken|doesn't work|unreliable|flaky|buggy|...)"),
    "opportunity": re.compile(r"(?:opportunity|untapped|need for|demand for|...)"),
}
```

Each pattern matches common English phrases that indicate an unmet need or frustration.

---

#### Composite Impact Scoring

Each pain signal is scored on four dimensions:

| Dimension | Weight | Source | Meaning |
|-----------|--------|--------|---------|
| **Trend** | 0.35 | Emerging topics | Does this signal relate to an accelerating keyword? |
| **Authority** | 0.25 | PageRank | Is the source blog influential? |
| **Breadth** | 0.25 | Blog count | How many distinct blogs express this pain? |
| **Recency** | 0.15 | Published date | How recent is the signal? (exponential decay) |

```python
impact_score = 0.35 * trend + 0.25 * authority + 0.25 * breadth + 0.15 * recency
```

---

#### Agglomerative Clustering

Related pain signals are grouped into coherent project idea themes using **agglomerative clustering** (not K-means).

**Why agglomerative, not K-means?**
- No need to specify K in advance (uses distance threshold instead)
- Works with precomputed cosine distance matrices
- Better for small, variable-sized clusters (pain signals may form many small groups)

```python
clustering = AgglomerativeClustering(
    n_clusters=None,                    # Auto-determine cluster count
    distance_threshold=1.0 - 0.3,      # Cosine similarity threshold of 0.3
    metric="precomputed",               # Use precomputed distance matrix
    linkage="average",                  # Average linkage for balanced clusters
)
```

---

#### Key Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `extract_pain_signals(conn)` | Scan posts for pain language | List of signal dicts with back-pointers |
| `extract_signal_keywords(signals)` | TF-IDF on signal texts | (vectorizer, matrix) tuple |
| `score_ideas(signals, emerging, centrality)` | Composite scoring | Signals with `impact_score` added |
| `build_justification(idea)` | Written explanation | Multi-sentence string |
| `cluster_signals(signals, vectorizer, matrix)` | Group into ideas | List of idea dicts |
| `generate_ideas(conn, ...)` | Full pipeline | List of ranked idea dicts |

---

### 2.9 Module: `reports.py`

**Purpose**: Generate Markdown and JSON reports from analysis results, including project ideas reports.

**Key Dependency**: `tabulate` - formats data into ASCII/Markdown tables (like Java's TextTable or Apache Commons Lang3's `TableFormatter`).

---

#### Tabulate Example

```python
from tabulate import tabulate

data = [
    ["Python", 42, 0.95],
    ["Java", 38, 0.82],
    ["Rust", 15, 0.67]
]

print(tabulate(data, headers=["Language", "Posts", "Score"], tablefmt="github"))
```

**Output**:
```markdown
| Language   |   Posts |   Score |
|------------|---------|---------|
| Python     |      42 |    0.95 |
| Java       |      38 |    0.82 |
| Rust       |      15 |    0.67 |
```

**Supported formats**: `github` (Markdown), `plain`, `grid`, `html`, `latex`.

---

#### Report Functions

| Function | Outputs | Description |
|----------|---------|-------------|
| `generate_summary_report()` | `summary.md` | Overview: dataset stats, top topics, top blogs, cluster summary, top ideas |
| `generate_trend_report()` | `trends.md`, `trends.json` | Emerging topics with acceleration, period summary |
| `generate_network_report()` | `network.md`, `network.json` | Graph stats, top blogs by PageRank and betweenness |
| `generate_cluster_report()` | `clusters.md`, `clusters.json` | Cluster assignments, similar blog pairs |
| `generate_ideas_report()` | `ideas.md`, `ideas.json` | Ranked project ideas with justifications, sources, key quotes |
| `generate_all_reports()` | All of the above | Convenience function to generate all reports (ideas included if provided) |

**JSON output**: For programmatic consumption (e.g., web dashboard).
**Markdown output**: For human reading (e.g., GitHub README).

---

### 2.10 Module: `cli.py`

**Purpose**: Command-line interface using Click.

**What is Click?**
A Python library for creating CLI tools with decorators (like Java annotations).

**Java equivalent**: Apache Commons CLI, Picocli, or JCommander.

---

#### Click Basics

```python
import click

@click.group()
def main():
    """HN Blog Intelligence Platform."""
    pass

@main.command()
@click.option("--opml", default="docs/hn-blogs.opml", help="Path to OPML file.")
@click.option("--timeout", default=30, type=int, help="Request timeout in seconds.")
def fetch(opml, timeout):
    """Fetch all RSS feeds and store posts."""
    click.echo(f"Fetching from {opml} with timeout {timeout}s")
    # Implementation...
```

**Decorator Explanation**:

| Decorator | Meaning | Java Equivalent |
|-----------|---------|-----------------|
| `@click.group()` | Command group (like `git` has `git commit`, `git push`) | Subcommand dispatcher |
| `@main.command()` | Subcommand of `main` | `@Command` annotation |
| `@click.option()` | Command-line option/flag | `@Option` annotation |
| `click.echo()` | Print to stdout (portable across platforms) | `System.out.println()` |

**Generated CLI**:
```bash
hn-intel --help
  Commands:
    fetch    Fetch all RSS feeds and store posts.
    status   Show database status.
    analyze  Run full analysis pipeline.
    ideas    Surface high-impact project ideas from blog pain signals.
    report   Run analysis and generate all reports.

hn-intel fetch --help
  Options:
    --opml TEXT       Path to OPML file.
    --timeout INTEGER Request timeout in seconds.
    --delay FLOAT     Delay between feed requests.
    --help            Show this message and exit.
```

---

#### Lazy Imports Inside Commands

```python
@main.command()
def fetch(opml, timeout, delay):
    """Fetch all RSS feeds and store posts."""
    from hn_intel.fetcher import fetch_all_feeds  # Import here, not at top

    conn = get_connection()
    summary = fetch_all_feeds(conn, opml_path=opml, timeout=timeout, delay=delay)
    conn.close()
```

**Why import inside function?**
- **Faster CLI startup**: `hn-intel --help` doesn't need to load heavy libraries (scikit-learn, networkx).
- **Import only what's needed**: `hn-intel status` doesn't import analysis modules.

**Trade-off**: Slightly slower when running the command (but imperceptible).

---

## 3. Database Schema Reference

### Schema: `blogs` Table

Stores metadata about each blog.

```sql
CREATE TABLE IF NOT EXISTS blogs (
    id INTEGER PRIMARY KEY,          -- Auto-increment (SQLite's ROWID alias)
    name TEXT,                       -- Blog display name (e.g., "Joel on Software")
    feed_url TEXT UNIQUE,            -- RSS feed URL (UNIQUE constraint for deduplication)
    site_url TEXT,                   -- Blog website URL
    last_fetched TEXT,               -- ISO timestamp of last fetch attempt
    fetch_status TEXT                -- "ok" or error message
);
```

**Columns**:
- **`id`**: Auto-incrementing primary key (like `SERIAL` in PostgreSQL or `AUTO_INCREMENT` in MySQL).
- **`feed_url`**: Unique constraint prevents duplicate blogs. Used by `INSERT OR IGNORE`.
- **`last_fetched`**: ISO 8601 string (e.g., `2024-03-15T14:30:00+00:00`). SQLite doesn't have native datetime type.
- **`fetch_status`**: Stores "ok" or exception message (truncated to 200 chars).

---

### Schema: `posts` Table

Stores individual blog posts.

```sql
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    blog_id INTEGER REFERENCES blogs(id),  -- Foreign key to blogs
    title TEXT,
    description TEXT,                      -- HTML content from RSS <description> or <summary>
    url TEXT UNIQUE,                       -- Post URL (UNIQUE for deduplication)
    published TEXT,                        -- ISO timestamp of publication
    author TEXT
);

CREATE INDEX IF NOT EXISTS idx_posts_blog_id ON posts(blog_id);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published);
```

**Indexes**:
- **`idx_posts_blog_id`**: Speed up `SELECT * FROM posts WHERE blog_id = ?` (used by analysis).
- **`idx_posts_published`**: Speed up date range queries and sorting.

**Why `url` is UNIQUE**:
- RSS feeds may repeat posts on pagination.
- Prevents duplicate posts across multiple fetches.

---

### Schema: `citations` Table

Stores cross-blog citations extracted from post descriptions.

```sql
CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY,
    source_post_id INTEGER REFERENCES posts(id),   -- Which post contains the citation
    source_blog_id INTEGER REFERENCES blogs(id),   -- Which blog wrote the post
    target_blog_id INTEGER REFERENCES blogs(id),   -- Which blog was cited
    target_url TEXT                                -- The actual URL found in the post
);

CREATE INDEX IF NOT EXISTS idx_citations_source_blog_id ON citations(source_blog_id);
CREATE INDEX IF NOT EXISTS idx_citations_target_blog_id ON citations(target_blog_id);
```

**Example Row**:
```
source_post_id: 123
source_blog_id: 5   (Joel on Software)
target_blog_id: 8   (Paul Graham)
target_url: "http://paulgraham.com/startupideas.html"
```

**Indexes**: Speed up graph queries (e.g., "all citations from blog X", "all citations to blog Y").

---

### Schema Relationships

**ER Diagram**:
```
blogs (1) ──< (N) posts
  ↑              ↓
  │(1)          (1)
  │              │
  └──< (N) citations (N) ──┘
```

- One blog has many posts (1:N)
- One post can have many citations (1:N)
- Citations link source blog to target blog (N:N via junction table)

---

## 4. Testing Guide

### 4.1 What is pytest?

**pytest** is a Python testing framework (like JUnit for Java or Google Test for C++).

**Key differences from JUnit**:

| Feature | pytest | JUnit |
|---------|--------|-------|
| Test discovery | Auto-discovers `test_*.py` files | Annotations (`@Test`) |
| Assertions | Plain `assert` statements | `assertEquals()`, `assertTrue()` |
| Setup/teardown | Fixtures (functions with `@pytest.fixture`) | `@Before`, `@After` |
| Test isolation | Each test gets fresh fixtures | Managed manually |

---

### 4.2 Running Tests

**Run all tests**:
```bash
python -m pytest tests/ -v
```

**Flags**:
- `-v`: Verbose output (shows each test name)
- `-s`: Show print statements (pytest captures stdout by default)
- `-k pattern`: Run tests matching pattern (e.g., `-k test_db`)
- `--tb=short`: Shorter traceback on failures

**Run a single test file**:
```bash
python -m pytest tests/test_db.py -v
```

**Run a specific test function**:
```bash
python -m pytest tests/test_db.py::test_init_db_creates_tables -v
```

**Example output**:
```
tests/test_db.py::test_init_db_creates_tables PASSED        [14%]
tests/test_db.py::test_upsert_blogs PASSED                   [28%]
tests/test_db.py::test_insert_post_dedup PASSED              [42%]
...
========================= 8 passed in 0.42s =========================
```

---

### 4.3 Test Structure

**Typical test file**:
```python
"""Tests for database layer."""

import sqlite3
import tempfile
import os

from hn_intel.db import init_db, upsert_blogs, get_blogs


def _temp_db():
    """Helper function to create a temporary in-memory database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn, path


def test_init_db_creates_tables():
    """Test that init_db creates all required tables."""
    conn, path = _temp_db()
    try:
        # Setup
        init_db(conn)

        # Execute
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t["name"] for t in tables]

        # Assert
        assert "blogs" in table_names
        assert "posts" in table_names
        assert "citations" in table_names
    finally:
        # Cleanup
        conn.close()
        os.unlink(path)
```

**Pattern**:
1. **Setup**: Create test data (temp database, sample objects)
2. **Execute**: Call the function under test
3. **Assert**: Check results with `assert` statements
4. **Cleanup**: Delete temp files, close connections (in `finally` block)

---

### 4.4 Assertions

**pytest uses plain Python `assert`**:

```python
# Equal
assert result == expected

# Not equal
assert result != unexpected

# Boolean
assert is_valid
assert not is_invalid

# Membership
assert "blogs" in table_names

# Length
assert len(rows) == 2

# Type
assert isinstance(result, dict)

# Exceptions
import pytest
with pytest.raises(ValueError):
    dangerous_function()
```

**On failure, pytest shows rich diffs**:
```
>       assert len(rows) == 2
E       assert 3 == 2
E        +  where 3 = len([...])
```

---

### 4.5 Fixtures (Setup/Teardown)

**Fixtures** are reusable setup functions.

```python
import pytest

@pytest.fixture
def temp_db():
    """Provide a temporary database connection."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    yield conn  # Test runs here

    # Cleanup after test
    conn.close()
    os.unlink(path)


def test_with_fixture(temp_db):
    """Test using the temp_db fixture."""
    init_db(temp_db)  # temp_db is passed automatically
    assert temp_db.execute("SELECT name FROM sqlite_master").fetchall()
```

**How it works**:
1. pytest sees `temp_db` argument in test function
2. Calls `temp_db()` fixture function
3. Runs code before `yield`, passes `conn` to test
4. Runs test
5. Runs cleanup code after `yield`

**Java equivalent**: `@Before` + `@After` in JUnit.

---

### 4.6 Writing a New Test (Step-by-Step Example)

**Scenario**: Test the `get_blog_domains()` function.

**Step 1: Create test file** (if not exists): `tests/test_db.py`

**Step 2: Import necessary modules**:
```python
from hn_intel.db import get_blog_domains, init_db, upsert_blogs
```

**Step 3: Write helper function** (if not exists):
```python
def _temp_db():
    """Create a temporary database connection."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn, path
```

**Step 4: Write test function**:
```python
def test_get_blog_domains():
    """Test that get_blog_domains correctly maps domains to blog IDs."""
    conn, path = _temp_db()
    try:
        # Setup: Initialize database
        init_db(conn)

        # Setup: Insert test blogs
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"},
            {"name": "Blog B", "feed_url": "https://b.com/feed", "site_url": "https://www.b.com"},
        ])

        # Execute: Call function under test
        domains = get_blog_domains(conn)

        # Assert: Check results
        assert "a.com" in domains
        assert "b.com" in domains  # www. should be stripped
        assert "www.b.com" not in domains

    finally:
        # Cleanup
        conn.close()
        os.unlink(path)
```

**Step 5: Run the test**:
```bash
python -m pytest tests/test_db.py::test_get_blog_domains -v
```

**Step 6: Verify it passes**:
```
tests/test_db.py::test_get_blog_domains PASSED
```

---

## 5. Adding New Features

### 5.1 Example 1: How to Add a New CLI Command

**Scenario**: Add a command `hn-intel export-csv` that exports all posts to a CSV file.

---

**Step 1: Create the business logic function**

Create `hn_intel/export.py`:
```python
"""Export data to CSV format."""

import csv

def export_posts_to_csv(conn, output_path):
    """Export all posts to a CSV file.

    Args:
        conn: sqlite3.Connection instance.
        output_path: Path to the output CSV file.

    Returns:
        Number of posts exported.
    """
    from hn_intel.db import get_all_posts

    posts = get_all_posts(conn)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["blog_name", "title", "url", "published"])
        writer.writeheader()

        for post in posts:
            writer.writerow({
                "blog_name": post["blog_name"],
                "title": post["title"],
                "url": post["url"],
                "published": post["published"],
            })

    return len(posts)
```

---

**Step 2: Add CLI command to `cli.py`**

Edit `hn_intel/cli.py`:
```python
@main.command()
@click.option("--output", default="posts.csv", help="Output CSV file path.")
def export_csv(output):
    """Export all posts to a CSV file."""
    from hn_intel.export import export_posts_to_csv

    conn = get_connection()
    init_db(conn)

    count = export_posts_to_csv(conn, output)
    conn.close()

    click.echo(f"Exported {count} posts to {output}")
```

---

**Step 3: Test the command**

```bash
# Reinstall to register new command
pip install -e .

# Run the command
hn-intel export-csv --output my_posts.csv

# Verify
cat my_posts.csv
```

---

**Step 4: Write a test**

Create `tests/test_export.py`:
```python
import tempfile
import os
import csv

from hn_intel.db import init_db, upsert_blogs, insert_post
from hn_intel.export import export_posts_to_csv


def test_export_posts_to_csv():
    """Test CSV export of posts."""
    import sqlite3

    # Create temp database
    fd_db, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd_db)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Create temp CSV file
    fd_csv, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd_csv)

    try:
        # Setup database with test data
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Test Blog", "feed_url": "https://test.com/feed", "site_url": "https://test.com"}
        ])
        blog_id = conn.execute("SELECT id FROM blogs").fetchone()["id"]
        insert_post(conn, blog_id, {
            "title": "Test Post",
            "description": "Test description",
            "url": "https://test.com/post-1",
            "published": "2024-01-01",
            "author": "Author"
        })

        # Export to CSV
        count = export_posts_to_csv(conn, csv_path)

        # Assert count
        assert count == 1

        # Read CSV and verify contents
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["title"] == "Test Post"
            assert rows[0]["blog_name"] == "Test Blog"

    finally:
        conn.close()
        os.unlink(db_path)
        os.unlink(csv_path)
```

Run test:
```bash
python -m pytest tests/test_export.py -v
```

---

### 5.2 Example 2: How to Add a New Analysis Function

**Scenario**: Add a function `compute_post_frequency(conn)` that returns posting frequency per blog.

---

**Step 1: Add function to `analyzer.py`**

Edit `hn_intel/analyzer.py`:
```python
def compute_post_frequency(conn):
    """Compute posting frequency (posts per month) for each blog.

    Args:
        conn: sqlite3.Connection instance.

    Returns:
        Dict mapping blog name to average posts per month.
    """
    from collections import defaultdict
    from datetime import datetime

    posts = get_all_posts(conn)

    blog_posts = defaultdict(list)
    for post in posts:
        published = post["published"]
        if published:
            try:
                date = datetime.fromisoformat(published[:10])
                blog_posts[post["blog_name"]].append(date)
            except ValueError:
                pass

    result = {}
    for blog_name, dates in blog_posts.items():
        if len(dates) < 2:
            result[blog_name] = 0.0
            continue

        dates_sorted = sorted(dates)
        first_date = dates_sorted[0]
        last_date = dates_sorted[-1]

        months = (last_date.year - first_date.year) * 12 + (last_date.month - first_date.month)
        if months == 0:
            months = 1

        result[blog_name] = len(dates) / months

    return result
```

---

**Step 2: Add to analysis pipeline (optional)**

Edit `cli.py` → `analyze` command to include this:
```python
@main.command()
def analyze(...):
    # ... existing code ...

    click.echo("Computing post frequency...")
    from hn_intel.analyzer import compute_post_frequency
    frequency = compute_post_frequency(conn)
    top_freq = sorted(frequency.items(), key=lambda x: x[1], reverse=True)[:5]

    click.echo("\nMost frequent posters:")
    for blog, freq in top_freq:
        click.echo(f"  {blog}: {freq:.2f} posts/month")
```

---

**Step 3: Write test**

Add to `tests/test_analyzer.py`:
```python
def test_compute_post_frequency():
    """Test post frequency computation."""
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Fast Blog", "feed_url": "https://fast.com/feed", "site_url": "https://fast.com"},
            {"name": "Slow Blog", "feed_url": "https://slow.com/feed", "site_url": "https://slow.com"},
        ])

        fast_id = conn.execute("SELECT id FROM blogs WHERE name='Fast Blog'").fetchone()["id"]
        slow_id = conn.execute("SELECT id FROM blogs WHERE name='Slow Blog'").fetchone()["id"]

        # Fast Blog: 10 posts in January 2024
        for i in range(10):
            insert_post(conn, fast_id, {
                "title": f"Post {i}",
                "description": "",
                "url": f"https://fast.com/post-{i}",
                "published": f"2024-01-{i+1:02d}",
                "author": ""
            })

        # Slow Blog: 1 post in January, 1 post in December (12 months)
        insert_post(conn, slow_id, {
            "title": "Post 1",
            "description": "",
            "url": "https://slow.com/post-1",
            "published": "2024-01-01",
            "author": ""
        })
        insert_post(conn, slow_id, {
            "title": "Post 2",
            "description": "",
            "url": "https://slow.com/post-2",
            "published": "2024-12-31",
            "author": ""
        })

        frequency = compute_post_frequency(conn)

        # Fast Blog: 10 posts in 0 months → 10.0 posts/month
        assert frequency["Fast Blog"] == 10.0

        # Slow Blog: 2 posts in 11 months → ~0.18 posts/month
        assert 0.1 < frequency["Slow Blog"] < 0.2

    finally:
        conn.close()
        os.unlink(path)
```

---

### 5.3 Example 3: How to Add a New Database Table

**Scenario**: Add a `tags` table to store user-defined tags for blogs.

---

**Step 1: Update schema in `db.py`**

Edit `hn_intel/db.py` → `init_db()`:
```python
def init_db(conn):
    """Create tables and indexes if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS blogs (...);
        CREATE TABLE IF NOT EXISTS posts (...);
        CREATE TABLE IF NOT EXISTS citations (...);

        -- NEW: Tags table
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            blog_id INTEGER REFERENCES blogs(id),
            tag TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tags_blog_id ON tags(blog_id);
        CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);

        ...existing indexes...
    """)
```

---

**Step 2: Add helper functions in `db.py`**

```python
def add_tag(conn, blog_id, tag):
    """Add a tag to a blog.

    Args:
        conn: sqlite3.Connection instance.
        blog_id: ID of the blog.
        tag: Tag string.
    """
    conn.execute("INSERT INTO tags (blog_id, tag) VALUES (?, ?)", (blog_id, tag))
    conn.commit()


def get_tags_for_blog(conn, blog_id):
    """Get all tags for a blog.

    Returns:
        List of tag strings.
    """
    rows = conn.execute("SELECT tag FROM tags WHERE blog_id = ?", (blog_id,)).fetchall()
    return [row["tag"] for row in rows]


def get_blogs_by_tag(conn, tag):
    """Get all blogs with a specific tag.

    Returns:
        List of sqlite3.Row objects (blogs).
    """
    return conn.execute("""
        SELECT b.* FROM blogs b
        JOIN tags t ON b.id = t.blog_id
        WHERE t.tag = ?
    """, (tag,)).fetchall()
```

---

**Step 3: Add CLI command**

Edit `cli.py`:
```python
@main.command()
@click.argument("blog_name")
@click.argument("tag")
def add_tag(blog_name, tag):
    """Add a tag to a blog."""
    from hn_intel.db import add_tag as db_add_tag, get_blogs

    conn = get_connection()
    init_db(conn)

    # Find blog by name
    blogs = [b for b in get_blogs(conn) if b["name"] == blog_name]
    if not blogs:
        click.echo(f"Blog '{blog_name}' not found.")
        return

    blog_id = blogs[0]["id"]
    db_add_tag(conn, blog_id, tag)
    conn.close()

    click.echo(f"Tagged '{blog_name}' with '{tag}'")
```

---

**Step 4: Write tests**

Add to `tests/test_db.py`:
```python
def test_tags():
    """Test tag CRUD operations."""
    conn, path = _temp_db()
    try:
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog A", "feed_url": "https://a.com/feed", "site_url": "https://a.com"}
        ])
        blog_id = conn.execute("SELECT id FROM blogs").fetchone()["id"]

        # Add tags
        add_tag(conn, blog_id, "python")
        add_tag(conn, blog_id, "machine-learning")

        # Get tags
        tags = get_tags_for_blog(conn, blog_id)
        assert "python" in tags
        assert "machine-learning" in tags

        # Get blogs by tag
        blogs = get_blogs_by_tag(conn, "python")
        assert len(blogs) == 1
        assert blogs[0]["name"] == "Blog A"

    finally:
        conn.close()
        os.unlink(path)
```

---

### 5.4 Example 4: How to Add a New Report Type

**Scenario**: Add a report `top_authors.md` that lists most prolific authors.

---

**Step 1: Create analysis function**

Add to `analyzer.py`:
```python
def compute_top_authors(conn, limit=20):
    """Find the most prolific authors by post count.

    Returns:
        List of dicts: {author, post_count}.
    """
    from collections import Counter

    posts = get_all_posts(conn)
    authors = [post["author"] for post in posts if post["author"]]

    counter = Counter(authors)
    return [{"author": author, "post_count": count}
            for author, count in counter.most_common(limit)]
```

---

**Step 2: Add report generation function**

Add to `reports.py`:
```python
def generate_authors_report(conn, output_dir):
    """Generate top authors report.

    Returns:
        Path to the generated authors.md file.
    """
    from hn_intel.analyzer import compute_top_authors

    os.makedirs(output_dir, exist_ok=True)

    authors = compute_top_authors(conn)

    lines = []
    lines.append("# Top Authors by Post Count\n")

    if authors:
        table_data = [[a["author"], a["post_count"]] for a in authors]
        lines.append(tabulate(table_data, headers=["Author", "Posts"], tablefmt="github"))
    else:
        lines.append("No author data available.")

    path = os.path.join(output_dir, "authors.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path
```

---

**Step 3: Integrate into `generate_all_reports()`**

Edit `reports.py`:
```python
def generate_all_reports(...):
    """Generate all reports at once."""
    paths = []

    # ... existing reports ...

    authors_path = generate_authors_report(conn, output_dir)
    paths.append(authors_path)

    return paths
```

---

**Step 4: Write test**

Add to `tests/test_reports.py`:
```python
def test_generate_authors_report():
    """Test authors report generation."""
    import tempfile
    import os

    conn, db_path = _temp_db()
    tmpdir = tempfile.mkdtemp()

    try:
        # Setup test data
        init_db(conn)
        upsert_blogs(conn, [
            {"name": "Blog", "feed_url": "https://blog.com/feed", "site_url": "https://blog.com"}
        ])
        blog_id = conn.execute("SELECT id FROM blogs").fetchone()["id"]

        insert_post(conn, blog_id, {
            "title": "Post 1", "description": "", "url": "https://blog.com/1",
            "published": "", "author": "Alice"
        })
        insert_post(conn, blog_id, {
            "title": "Post 2", "description": "", "url": "https://blog.com/2",
            "published": "", "author": "Alice"
        })
        insert_post(conn, blog_id, {
            "title": "Post 3", "description": "", "url": "https://blog.com/3",
            "published": "", "author": "Bob"
        })

        # Generate report
        path = generate_authors_report(conn, tmpdir)

        # Verify file exists
        assert os.path.exists(path)

        # Verify content
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Alice" in content
            assert "Bob" in content
            assert "2" in content  # Alice's post count

    finally:
        conn.close()
        os.unlink(db_path)
        import shutil
        shutil.rmtree(tmpdir)
```

---

## 6. Code Conventions

### 6.1 Module Structure

Every Python module (`.py` file) should follow this order:

```python
"""Module docstring: brief description of the module."""

# 1. Standard library imports (alphabetical)
import html
import os
import re
from collections import defaultdict
from datetime import datetime

# 2. Third-party imports (alphabetical)
import click
import feedparser
from sklearn.feature_extraction.text import TfidfVectorizer

# 3. Local imports (relative to project)
from hn_intel.db import get_all_posts, get_connection

# 4. Constants (UPPER_SNAKE_CASE)
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# 5. Functions and classes (in logical order, not alphabetical)
def main_function():
    """Primary function."""
    pass

def helper_function():
    """Supporting function."""
    pass

# 6. Main entry point (if applicable)
if __name__ == "__main__":
    main_function()
```

---

### 6.2 Naming Conventions

| Type | Convention | Examples |
|------|------------|----------|
| **Functions** | `snake_case`, verb-first | `get_user_by_id()`, `calculate_total()`, `is_valid()` |
| **Variables** | `snake_case`, descriptive | `user_count`, `is_valid`, `post_data` |
| **Constants** | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `API_URL`, `DEFAULT_TIMEOUT` |
| **Classes** | `PascalCase` | `UserService`, `DataValidator`, `BlogPost` |
| **Modules/Files** | `snake_case` | `db.py`, `opml_parser.py`, `network.py` |
| **Private** | Prefix with `_` | `_normalize_domain()`, `_temp_db()` |

**Private functions** (`_function_name`):
- Not imported by `from module import *`
- Convention only (Python doesn't enforce privacy)
- Use for internal helpers not part of public API

---

### 6.3 Docstring Format (Google Style)

```python
def fetch_all_feeds(conn, opml_path="docs/hn-blogs.opml", timeout=30, delay=0.5):
    """Fetch all feeds from an OPML file and insert posts into the database.

    This function reads an OPML file, fetches each RSS feed via HTTP, parses
    the feed entries, and stores new posts in the database. It includes error
    handling for individual feed failures and rate limiting between requests.

    Args:
        conn: sqlite3.Connection instance (already initialized).
        opml_path: Path to the OPML file. Defaults to "docs/hn-blogs.opml".
        timeout: Request timeout in seconds per feed. Defaults to 30.
        delay: Delay in seconds between feed requests. Defaults to 0.5.

    Returns:
        Dict with summary stats:
            - feeds_ok: Number of successfully fetched feeds.
            - feeds_err: Number of feeds that failed.
            - new_posts: Number of new posts inserted.
            - skipped: Number of duplicate posts skipped.

    Raises:
        FileNotFoundError: If the OPML file doesn't exist.

    Example:
        >>> conn = get_connection()
        >>> summary = fetch_all_feeds(conn, timeout=60)
        >>> print(f"Fetched {summary['new_posts']} new posts")
    """
```

**Sections**:
1. **One-line summary**: Brief description (imperative mood).
2. **Extended description** (optional): More details if needed.
3. **Args**: Parameter descriptions (name: description).
4. **Returns**: What the function returns.
5. **Raises** (optional): Exceptions that may be raised.
6. **Example** (optional): Usage example.

---

### 6.4 Error Handling Patterns

**Pattern 1: Validate early, fail fast**
```python
def process_data(data):
    """Process data with early validation."""
    if not data:
        raise ValueError("Data is required")
    if not isinstance(data, list):
        raise TypeError("Data must be a list")

    # Now safe to process
    for item in data:
        ...
```

**Pattern 2: Per-item error handling (continue on failure)**
```python
def process_items(items):
    """Process items, logging errors but continuing."""
    success_count = 0
    error_count = 0

    for item in items:
        try:
            process_item(item)
            success_count += 1
        except Exception as exc:
            print(f"Error processing {item}: {exc}")
            error_count += 1

    return {"success": success_count, "errors": error_count}
```

**Pattern 3: Return success/error dict**
```python
def risky_operation():
    """Return dict indicating success or failure."""
    try:
        result = do_something()
        return {"success": True, "data": result}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
```

**Pattern 4: Cleanup with `finally`**
```python
def process_file(path):
    """Always close file, even on error."""
    f = open(path, "r")
    try:
        data = f.read()
        process(data)
    finally:
        f.close()  # Runs even if exception occurs

# Better: Use context manager
def process_file(path):
    """Automatically closes file."""
    with open(path, "r") as f:  # Equivalent to try/finally
        data = f.read()
        process(data)
```

---

### 6.5 Database Access Patterns

**Always pass `conn`, never create connections inside modules**:

**Good**:
```python
def get_all_posts(conn):
    """Fetch all posts."""
    return conn.execute("SELECT * FROM posts").fetchall()

# Caller controls connection lifecycle
conn = get_connection()
posts = get_all_posts(conn)
conn.close()
```

**Bad**:
```python
def get_all_posts():
    """Fetch all posts."""
    conn = get_connection()  # Bad: Hidden dependency
    posts = conn.execute("SELECT * FROM posts").fetchall()
    conn.close()
    return posts
```

**Why?**
- **Testability**: Easy to pass in-memory test database.
- **Transaction control**: Caller controls commit/rollback.
- **Connection pooling**: Caller can reuse connections.

---

## 7. Dependency Reference

### 7.1 Core Dependencies

#### `feedparser` (>= 6.0, < 7.0)

**What it does**: Parses RSS, Atom, and RDF feeds into Python dicts.

**Why we use it**: Handles all feed formats and malformed XML gracefully.

**Java equivalent**: Rome library.

**C++ equivalent**: libmrss or custom XML parsing.

**Version constraint**: `>=6.0,<7.0` means "any version from 6.0 to 6.999, but not 7.0".
**Reason**: API breaks in major versions. We support 6.x only.

**Example**:
```python
import feedparser
feed = feedparser.parse("https://example.com/rss")
for entry in feed.entries:
    print(entry.title, entry.link)
```

---

#### `click` (>= 8.0, < 9.0)

**What it does**: Creates command-line interfaces with decorators.

**Why we use it**: Clean API, automatic help generation, argument parsing.

**Java equivalent**: Picocli, JCommander.

**C++ equivalent**: Boost.Program_options, CLI11.

**Example**:
```python
import click

@click.command()
@click.option("--name", default="World", help="Name to greet.")
def hello(name):
    click.echo(f"Hello, {name}!")

if __name__ == "__main__":
    hello()
```

---

#### `scikit-learn` (>= 1.3, < 2.0)

**What it does**: Machine learning library (TF-IDF, K-means, cosine similarity, etc.).

**Why we use it**: Industry-standard, efficient, well-documented.

**Java equivalent**: Weka, Smile.

**C++ equivalent**: MLpack, Shark.

**Key modules we use**:
- `sklearn.feature_extraction.text.TfidfVectorizer`: TF-IDF vectorization
- `sklearn.cluster.KMeans`: K-means clustering
- `sklearn.metrics.pairwise.cosine_similarity`: Cosine similarity

---

#### `networkx` (>= 3.0, < 4.0)

**What it does**: Graph/network analysis (PageRank, centrality, shortest paths).

**Why we use it**: Pure Python, easy API, comprehensive algorithms.

**Java equivalent**: JGraphT.

**C++ equivalent**: Boost Graph Library.

**Example**:
```python
import networkx as nx

G = nx.DiGraph()
G.add_edge("A", "B", weight=5)
G.add_edge("B", "C", weight=3)

pagerank = nx.pagerank(G, weight="weight")
print(pagerank)  # {'A': 0.33, 'B': 0.39, 'C': 0.28}
```

---

#### `tabulate` (>= 0.9, < 1.0)

**What it does**: Formats tables in ASCII, Markdown, HTML, LaTeX.

**Why we use it**: Generates Markdown tables for reports.

**Java equivalent**: TextTable, Apache Commons Lang3.

**Example**:
```python
from tabulate import tabulate

data = [["Alice", 42], ["Bob", 38]]
print(tabulate(data, headers=["Name", "Age"], tablefmt="github"))
```

---

#### `tqdm` (>= 4.65, < 5.0)

**What it does**: Progress bars for loops.

**Why we use it**: User feedback during long-running operations (feed fetching).

**Java equivalent**: ProgressBar, me.tongfei:progressbar.

**Example**:
```python
from tqdm import tqdm
import time

for i in tqdm(range(100)):
    time.sleep(0.01)
# Output: 100%|██████████| 100/100 [00:01<00:00, 99.12it/s]
```

---

#### `requests` (>= 2.31, < 3.0)

**What it does**: HTTP client library.

**Why we use it**: Simpler API than `urllib`, widely used standard.

**Java equivalent**: Apache HttpClient, OkHttp.

**C++ equivalent**: libcurl, cpr.

**Example**:
```python
import requests

resp = requests.get("https://api.github.com/users/github")
print(resp.json()["name"])  # "GitHub"
```

---

### 7.2 Dev Dependencies

#### `pytest` (>= 7.0, < 9.0)

**What it does**: Testing framework.

**Why we use it**: Clean syntax, powerful fixtures, great error messages.

**Java equivalent**: JUnit 5.

**C++ equivalent**: Google Test, Catch2.

---

## 8. Glossary

### RSS (Really Simple Syndication)
XML format for web feeds. Blogs publish RSS feeds listing recent posts. Example:
```xml
<rss version="2.0">
  <channel>
    <item>
      <title>My Blog Post</title>
      <link>https://example.com/post-1</link>
      <description>Post content...</description>
    </item>
  </channel>
</rss>
```

---

### OPML (Outline Processor Markup Language)
XML format for lists of RSS feeds. Used by feed readers to import/export subscriptions.

---

### TF-IDF (Term Frequency × Inverse Document Frequency)
Statistical measure of word importance in a document within a corpus.

**TF (Term Frequency)**: How often a word appears in this document.
**IDF (Inverse Document Frequency)**: How rare the word is across all documents.
**TF-IDF = TF × IDF**: High if word is frequent in this doc but rare overall.

**Example**: In a Python tutorial, "Python" has high TF. Across all programming tutorials, "Python" is common (low IDF). But "asyncio" is rare (high IDF), so "asyncio" gets a high TF-IDF score in Python tutorials.

---

### Cosine Similarity
Measure of similarity between two vectors based on the angle between them.

**Formula**: `cos(θ) = (A · B) / (||A|| × ||B||)`

**Range**: 0 to 1 (for non-negative vectors like TF-IDF).
**Interpretation**:
- 1.0 = Identical
- 0.5 = Moderately similar
- 0.0 = No overlap

---

### K-means Clustering
Algorithm to partition data into K groups (clusters) by minimizing distance to cluster centers.

**Steps**:
1. Choose K random centroids
2. Assign each point to nearest centroid
3. Recompute centroids as mean of assigned points
4. Repeat 2-3 until convergence

**Output**: Each item is assigned a cluster ID (0 to K-1).

---

### PageRank
Algorithm (invented by Google founders) that ranks nodes in a graph by importance.

**Intuition**: A node is important if many important nodes link to it.

**Random walk analogy**: If you randomly follow links, PageRank is the probability of ending up at a node.

**Formula**: Iteratively computed until convergence.

---

### Betweenness Centrality
Measure of how often a node lies on shortest paths between other nodes.

**Intuition**: High betweenness = "bridge" connecting different communities.

**Example**: In a social network, person C knows both the Python community and the Rust community. C has high betweenness.

---

### Sparse Matrix
Matrix where most values are 0. Stored efficiently (only non-zero values).

**Example** (TF-IDF matrix):
```
Dense:  [[0.5, 0.0, 0.0, 0.8],
         [0.0, 0.0, 0.7, 0.0],
         [0.0, 0.9, 0.0, 0.0]]

Sparse: {(0,0): 0.5, (0,3): 0.8, (1,2): 0.7, (2,1): 0.9}
```

**Why important**: TF-IDF matrices for 1000 docs × 500 words are mostly zeros. Sparse storage saves memory.

---

### Vectorizer (TfidfVectorizer)
Converts text documents into numerical feature vectors (TF-IDF scores).

**Input**: List of text strings.
**Output**: Sparse matrix (rows = documents, columns = words).

---

### Centroid
The "center" of a cluster in K-means. Computed as the mean of all points in the cluster.

**Example**: Cluster 1 has blogs with vectors `[0.8, 0.2]`, `[0.7, 0.3]`, `[0.9, 0.1]`. Centroid = `[0.8, 0.2]` (mean).

---

### N-gram
Sequence of N words.

**1-gram (unigram)**: Single word ("machine")
**2-gram (bigram)**: Two words ("machine learning")
**3-gram (trigram)**: Three words ("deep neural network")

**Why useful**: "Machine learning" is more meaningful than "machine" + "learning" separately.

---

### Token Pattern
Regex that defines what constitutes a "word" (token) for TF-IDF.

**Our pattern**: `r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b"`
**Matches**: "Python", "API", "v8engine"
**Ignores**: "a", "x", "123", "4chan" (starts with digit)

---

### Stop Words
Common words filtered out because they carry little meaning ("the", "is", "and").

**Why filter**: Focus analysis on meaningful words.

**Example**: "The quick brown fox" → "quick brown fox" (after removing "the").

---

### Min DF (Minimum Document Frequency)
Minimum number of documents a word must appear in to be included in TF-IDF.

**Example**: `min_df=3` means word must appear in at least 3 documents. Filters out typos and rare words.

---

### Max DF (Maximum Document Frequency)
Maximum fraction of documents a word can appear in.

**Example**: `max_df=0.7` means word must appear in at most 70% of documents. Filters out overly common words.

---

### Acceleration (in Emerging Topics)
Ratio of recent average to historical average for a keyword's TF-IDF score.

**Formula**: `acceleration = recent_avg / historical_avg`

**Example**: "chatgpt" scored 0.05 historically, 1.12 recently. Acceleration = 22.4x (emerging topic).

---

### In-Degree / Out-Degree (Graph Theory)
**In-degree**: Number of incoming edges (citations received).
**Out-degree**: Number of outgoing edges (citations made).

**Example**: Blog A cites 5 blogs (out-degree = 5). Blog A is cited by 10 blogs (in-degree = 10).

---

### Citation (in Network Analysis)
When Blog A links to Blog B in a post description, that's a citation from A to B.

**Represented as**: Directed edge in a graph (A → B).

---

### SQLite Row Factory
Configuration that changes how rows are returned from queries.

**Default**: Tuples `(1, 'Alice', 'alice@example.com')`
**With `sqlite3.Row`**: Dict-like `{'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}`

**Code**: `conn.row_factory = sqlite3.Row`

---

### PRAGMA (SQLite)
SQLite command to configure database behavior.

**Examples**:
- `PRAGMA journal_mode=WAL`: Enable Write-Ahead Logging (better concurrency).
- `PRAGMA foreign_keys=ON`: Enable foreign key constraints.

---

### INSERT OR IGNORE (SQLite)
Insert row, but if a UNIQUE constraint fails, silently skip (no error, no insert).

**Example**:
```sql
INSERT OR IGNORE INTO blogs (feed_url, name) VALUES ('https://example.com/feed', 'Blog');
-- If feed_url already exists, this does nothing (no error)
```

---

### Virtual Environment (venv)
Isolated Python environment with its own packages, separate from system Python.

**Analogy**: Like a project-specific JDK + classpath in Java.

**Create**: `python -m venv venv`
**Activate**: `venv\Scripts\activate` (Windows), `source venv/bin/activate` (Mac/Linux)

---

### Editable Install (pip -e)
Install a package in "development mode" where changes to source code take effect immediately without reinstalling.

**Command**: `pip install -e .`

**Analogy**: Like Maven's `mvn install` that links to source instead of copying JARs.

---

### Entry Point (project.scripts)
Configuration in `pyproject.toml` that creates a command-line executable.

**Example**:
```toml
[project.scripts]
hn-intel = "hn_intel.cli:main"
```

Creates command `hn-intel` that calls `main()` function in `hn_intel/cli.py`.

---

## Conclusion

You now have a comprehensive understanding of:
- Development environment setup (Python, venv, pip)
- Architecture (CLI, business logic, data layer)
- Each module's purpose and implementation
- Database schema and access patterns
- Testing with pytest
- Adding new features (commands, analysis, tables, reports)
- Code conventions and best practices
- All dependencies and their purpose
- Technical terminology

**Next steps**:
1. Set up your environment following Section 1
2. Run the existing tests to verify setup
3. Explore the codebase using this guide as reference
4. Try adding a simple feature (e.g., new CLI command)
5. Write tests for your feature

**Need help?** Re-read the relevant section or search for specific terms in the Glossary.

Happy coding!
