# User Guide

**For newcomers to Python, command-line tools, and data analysis**

---

## Table of Contents

- [Part 1: Getting Started](#part-1-getting-started)
- [Part 2: Use Cases](#part-2-use-cases)
- [Part 3: Understanding the Output](#part-3-understanding-the-output)
- [Part 4: Command Reference](#part-4-command-reference)
- [Part 5: FAQ & Troubleshooting](#part-5-faq--troubleshooting)

---

## Part 1: Getting Started

### What is this tool?

HN Blog Intelligence mines 92 popular Hacker News tech blogs for **project ideas** — things developers wish existed, struggle with, or find broken. It reads blog posts, detects pain-point language, and clusters related signals into ranked, actionable ideas backed by real evidence.

**No coding required.** You type commands and read the reports it generates.

---

### What you need

1. **Python 3.10+** — Check: `python --version`. Install from [python.org](https://www.python.org/downloads/).
2. **A terminal** — Windows: search "Command Prompt". Mac: search "Terminal". Linux: `Ctrl+Alt+T`.
3. **Internet connection** — For downloading blog posts (~2 minutes).

---

### Installation

#### Step 1: Open your terminal

#### Step 2: Navigate to the project folder

```bash
cd /path/to/hn-blog-intelligence
```

#### Step 3: Create a virtual environment

A **virtual environment** keeps this project's tools separate from your system Python.

```bash
python -m venv .venv
```

#### Step 4: Activate the virtual environment

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt. You need to activate this **every time** you open a new terminal.

#### Step 5: Install

```bash
pip install -e ".[dev]"
```

#### Step 6: Verify

```bash
hn-intel --help
```

You should see the CLI help showing available commands.

---

## Part 2: Use Cases

### Use Case 1: Fetch blog posts

**What you'll learn:** How to download blog posts from 92 tech blogs.

```bash
hn-intel fetch
```

**What happens:** The tool visits 92 blog RSS feeds, downloads their posts, and stores them in a local database. Takes **2-3 minutes**.

```
Fetching 92 feeds...
  [####################################]  100%
Feeds OK: 87
Feeds errored: 5
New posts: 2363
Skipped (duplicate): 0
```

- **Feeds errored: 5** — Some blogs are slow or offline. This is normal.
- **Skipped (duplicate): 0** — On subsequent fetches, already-stored posts are skipped.

---

### Use Case 2: Check your database

```bash
hn-intel status
```

```
Blogs: 92
Posts: 2363
Last fetch: 2026-02-09 22:23:15
```

Run this before generating ideas to make sure you have data.

---

### Use Case 3: Discover project ideas

**What you'll learn:** How to surface project ideas from developer pain signals.

```bash
hn-intel ideas
```

**What happens:** The tool scans all blog posts for pain-point language — phrases where bloggers express wishes, frustrations, gaps, or difficulties. It scores each signal by trend momentum, blog authority, breadth across blogs, and recency, then clusters related signals into coherent project ideas. Takes **30-60 seconds**.

```
Surfacing project ideas...
Found 15 project ideas:

  1. Simplified Database Migration
     Impact: 0.72 | Blogs: 4 | Signals: 7
     "It is hard to run zero-downtime database migrations...."
     Sources:
       - simonwillison.net: https://simonwillison.net/2026/...
       - xeiaso.net: https://xeiaso.net/blog/...
       - fasterthanli.me: https://fasterthanli.me/articles/...

  2. Reliable DNS Resolution
     Impact: 0.65 | Blogs: 3 | Signals: 5
     ...
```

**What the numbers mean:**
- **Impact (0 to 1):** Composite score. Higher = stronger signal.
- **Blogs:** How many distinct blogs expressed this pain point. More = more validation.
- **Signals:** Total pain expressions found for this idea.

---

### Use Case 4: Save ideas to files

```bash
hn-intel ideas --output-dir output
```

This generates two files:
- `output/ideas.md` — Full report with justifications, evidence, and context quotes
- `output/ideas.json` — Machine-readable version

Open `output/ideas.md` in any text editor to read the detailed report.

---

### Use Case 5: Update your data

```bash
hn-intel fetch
```

Run the same fetch command again. The tool only adds **new** posts (duplicates are skipped by URL).

```
New posts: 15
Skipped (duplicate): 2348
```

**How often to fetch:**
- Before each analysis: ensures fresh data
- Weekly: good for tracking trends over time
- Daily: if you want the latest posts

---

## Part 3: Understanding the Output

### ideas.md — The main report

Each idea in the report includes:

#### Impact Score and Metadata

```markdown
## 1. Simplified Database Migration
**Impact Score**: 0.72 | **Blogs**: 4 | **Signals**: 7
```

The impact score (0 to 1) combines four factors:
- **Trend momentum (35%)**: Does this pain relate to an accelerating topic?
- **Authority (25%)**: Is the source blog influential (cited by many other blogs)?
- **Breadth (25%)**: How many distinct blogs express this pain?
- **Recency (15%)**: How recently was this pain expressed?

#### Justification

A written explanation of why this idea has high impact, including which blogs contributed and what pain types were detected.

#### Evidence

Evidence is grouped by source post. Each post appears once with all its pain signals listed:

```markdown
### Evidence

#### [Post Title](url) — blog-name.com
**Date**: 2025-11-22

- **Pain type**: difficulty | **Found**: midway through
  > ...it becomes **difficult to draw conclusions**...

- **Pain type**: broken | **Found**: near the beginning
  > ...**evals are largely unreliable**...
```

The context blockquote shows the surrounding sentences, with the matched pain phrase **bolded**.

#### Idea Labels

Labels are generated from the dominant pain type and keywords from post titles:

| Pain Type | Label Template | Example |
|-----------|---------------|---------|
| Wish | "Better ..." | Better Log Correlation |
| Frustration | "Improved ..." | Improved CI Pipeline |
| Gap | "... Solution" | Observability Solution |
| Difficulty | "Simplified ..." | Simplified Database Migration |
| Broken | "Reliable ..." | Reliable DNS Resolution |
| Opportunity | "... Platform" | Edge Runtime Platform |

### ideas.json — Machine-readable data

Same content as ideas.md in JSON format. Useful for building dashboards, filtering ideas programmatically, or feeding into other tools.

---

## Part 4: Command Reference

### hn-intel fetch

Download blog posts from RSS feeds.

| Option | Default | Description |
|--------|---------|-------------|
| `--opml` | `docs/hn-blogs.opml` | Path to the OPML file listing blog feeds |
| `--timeout` | `30` | HTTP timeout per feed (seconds) |
| `--delay` | `0.5` | Delay between requests (seconds) |

```bash
hn-intel fetch
hn-intel fetch --timeout 60 --delay 1.0
hn-intel fetch --opml my-custom-blogs.opml
```

### hn-intel status

Show database statistics. No options.

```bash
hn-intel status
```

### hn-intel ideas

Surface project ideas from blog pain signals.

| Option | Default | Description |
|--------|---------|-------------|
| `--max-features` | `500` | TF-IDF vocabulary size |
| `--top-n` | `20` | Maximum ideas to surface |
| `--period` | `month` | Trend period: `month` or `week` |
| `--output-dir` | None | Save ideas.md and ideas.json to this directory |

```bash
hn-intel ideas
hn-intel ideas --top-n 10 --output-dir output
hn-intel ideas --period week --output-dir output
```

**Tip:** Use `--period week` for finer-grained trend detection (what's hot this week vs. last week).

---

## Part 5: FAQ & Troubleshooting

### Setup

**Q: `python: command not found`**
Install Python from [python.org](https://www.python.org/downloads/). On Windows, check "Add Python to PATH" during installation.

**Q: `pip: command not found`**
Try `python -m pip install -e ".[dev]"` instead.

**Q: Virtual environment activation doesn't work**
Windows PowerShell users may need: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Q: `hn-intel: command not found`**
Make sure your virtual environment is activated (you should see `(.venv)` in your prompt). Then reinstall: `pip install -e ".[dev]"`.

---

### Fetching

**Q: Some feeds errored**
Normal. Blogs go offline or have slow servers. 80+ successful feeds is typical.

**Q: 0 new posts**
You already have all available posts. Blogs don't post every day.

**Q: Can I add my own blogs?**
Yes. Edit `docs/hn-blogs.opml` and add an entry:
```xml
<outline text="Blog Name" title="Blog Name" type="rss" xmlUrl="https://example.com/feed.xml" htmlUrl="https://example.com"/>
```
Then run `hn-intel fetch`.

---

### Ideas

**Q: How does scoring work?**
Each pain signal gets a composite score: trend momentum (35%) + blog authority (25%) + breadth across blogs (25%) + recency (15%). The idea's score is the maximum across all its member signals.

**Q: Why are some ideas filtered out?**
Ideas backed by only a single blog are removed. Cross-validation from 2+ independent blogs is required.

**Q: Posts seem old**
Posts older than 12 months are automatically excluded from the analysis.

**Q: Can I export to Excel?**
Open `ideas.json` and use an online JSON-to-CSV converter, or copy the tables from `ideas.md` directly.

**Q: Where is the data stored?**
In `data/hn_intel.db` — a SQLite database file. You can explore it with [DB Browser for SQLite](https://sqlitebrowser.org/).

**Q: Do I need a GPU?**
No. All algorithms (TF-IDF, clustering, PageRank) are classical ML and run fast on any CPU.

---

### Errors

**Q: `Database is locked`**
Close other terminals running `hn-intel` commands.

**Q: `Permission denied` on activation**
Windows PowerShell: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
Mac/Linux: use `source .venv/bin/activate` (not just the path).

**Q: `No module named 'hn_intel'`**
Activate your virtual environment and run `pip install -e ".[dev]"`.

---

### Learn More

For a detailed trace of how a blog post becomes a project idea (with real scoring arithmetic), see **[Ideas Pipeline Deep Dive](IDEAS_PIPELINE_DEEP_DIVE.md)**.
