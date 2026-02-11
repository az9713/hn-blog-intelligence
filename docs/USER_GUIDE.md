# HN Blog Intelligence Platform - User Guide

**For newcomers to Python, command-line tools, and data analysis**

Last updated: February 2026

---

## Table of Contents

- [Part 1: Getting Started](#part-1-getting-started)
- [Part 2: Quick Start - 10 Use Cases](#part-2-quick-start---10-use-cases)
- [Part 3: Understanding the Output Files](#part-3-understanding-the-output-files)
- [Part 4: Command Reference](#part-4-command-reference)
- [Part 5: FAQ & Troubleshooting](#part-5-faq--troubleshooting)

---

## Part 1: Getting Started

### What is this tool?

The **HN Blog Intelligence Platform** is a command-line tool that analyzes blog posts from 92 popular technology blogs frequently shared on Hacker News. Think of it as a "trend detector" for the tech blogging world.

**What it does:**
- Downloads and stores blog posts from 92 tech blogs (via their RSS feeds)
- Identifies trending topics across these blogs
- Discovers which blogs reference each other
- Groups blogs with similar content together
- **Surfaces actionable project ideas** from pain points expressed in blog posts
- Generates easy-to-read reports about what's hot in tech

**What you'll learn:**
- Which topics are "heating up" in the tech community
- Which blogs are most influential (most-cited by others)
- Which blogs write about similar topics (so you can discover new blogs to read)
- How tech conversations evolve over time
- **What tools and solutions developers are wishing for** — backed by real blog evidence

**No coding required.** You just type commands and read the reports it generates.

---

### What you need before starting

#### 1. Python 3.10 or newer

Python is a programming language. Even though you won't be writing code, this tool is *built with* Python, so you need Python installed on your computer.

**Check if you have Python:**
```bash
python --version
```

**What you should see:**
```
Python 3.10.5
```
(or any version that starts with `3.10`, `3.11`, `3.12`, etc.)

**If you don't have Python or have an older version:**
- Windows: Download from [python.org](https://www.python.org/downloads/)
- Mac: Python 3 is usually pre-installed, but you can update via [python.org](https://www.python.org/downloads/) or Homebrew (`brew install python3`)
- Linux: Use your package manager (`sudo apt install python3` on Ubuntu/Debian)

#### 2. A terminal (command prompt)

A **terminal** (also called "command prompt" or "command line") is a text-based interface where you type commands.

**How to open a terminal:**
- **Windows**: Press `Win + R`, type `cmd`, press Enter
  - Or search for "Command Prompt" in the Start menu
- **Mac**: Press `Cmd + Space`, type `terminal`, press Enter
- **Linux**: Press `Ctrl + Alt + T`

**What is a terminal?** Think of it as a way to talk to your computer by typing instructions instead of clicking buttons. You'll type commands like `hn-intel fetch`, press Enter, and the program will run.

#### 3. Internet connection

The tool downloads blog posts from the internet, so you'll need a stable connection. The first download takes 2-3 minutes.

#### 4. A text editor

You'll need a way to view the reports this tool generates. Any of these work:
- **Notepad** (Windows)
- **TextEdit** (Mac)
- **VS Code, Sublime Text, Notepad++** (if you have them)

---

### Installation walkthrough

Follow these steps **exactly**. Every keystroke matters.

#### Step 1: Open your terminal

(See above for how to open a terminal on your operating system.)

#### Step 2: Navigate to the project folder

This project is already downloaded to your computer. You need to "navigate" to it in the terminal.

**On Windows:**
```bash
cd C:\Users\simon\Downloads\hn_popular_blogs_bestpartnerstv
```

**On Mac/Linux:**
```bash
cd /Users/YourName/Downloads/hn_popular_blogs_bestpartnerstv
```

Replace `YourName` with your actual username. If you're not sure of the exact path, you can drag the folder from Finder/Explorer into the terminal window, and it will paste the full path.

**What does `cd` mean?** "Change directory" - it's like double-clicking on a folder, but in the terminal.

#### Step 3: Create a virtual environment

A **virtual environment** is like a private sandbox for Python tools. It keeps this project's tools separate from other Python projects on your computer, preventing conflicts.

**Type this command:**
```bash
python -m venv .venv
```

**What this does:** Creates a folder called `.venv` inside the project folder. This folder will hold all the Python tools this project needs.

**Wait 10-30 seconds.** You'll see no output - that's normal. When your command prompt returns, it's done.

#### Step 4: Activate the virtual environment

Now you need to "enter" the sandbox you just created.

**On Windows:**
```bash
.venv\Scripts\activate
```

**On Mac/Linux:**
```bash
source .venv/bin/activate
```

**What you'll see:** Your command prompt will change. You'll see `(.venv)` at the beginning of the line:
```
(.venv) C:\Users\simon\Downloads\hn_popular_blogs_bestpartnerstv>
```

This means the virtual environment is active. You'll need to do this **every time** you open a new terminal and want to use this tool.

#### Step 5: Install the tool and its dependencies

Now install the actual software:

```bash
pip install -e ".[dev]"
```

**What does this mean?**
- `pip` is Python's "app store" - it installs tools
- `install` means "download and install"
- `-e` means "editable mode" - install from this folder
- `".[dev]"` means "install this project (the `.`) plus developer tools (`dev`)"

**What you'll see:** Lots of text scrolling by as it downloads and installs libraries. This takes 30-60 seconds.

**When it's done, you'll see:**
```
Successfully installed hn-intel-0.1.0 click-8.1.7 feedparser-6.0.10 ...
```

#### Step 6: Verify installation

Check that everything worked:

```bash
hn-intel --help
```

**What you should see:**
```
Usage: hn-intel [OPTIONS] COMMAND [ARGS]...

  HN Blog Intelligence Platform.

Options:
  --help  Show this message and exit.

Commands:
  analyze  Run full analysis pipeline and print summary.
  fetch    Fetch all RSS feeds and store posts.
  report   Run analysis and generate all reports.
  status   Show database status.
```

**If you see this, you're all set!** If you see an error, check [Part 5: Troubleshooting](#part-5-faq--troubleshooting).

---

## Part 2: Quick Start - 11 Use Cases

Each use case below teaches you one thing you can do with this tool. Follow them in order.

---

### Use Case 1: Fetch all blog posts

**What you'll learn:** How to download blog posts from 92 tech blogs

**Command:**
```bash
hn-intel fetch
```

**What happens:**
The tool visits 92 blog RSS feeds, downloads their latest posts, and stores them in a local database. This takes **2-3 minutes**.

**What you'll see:**
```
Fetching 92 feeds...
  [####################################]  100%
Feeds OK: 87
Feeds errored: 5
New posts: 2363
Skipped (duplicate): 0
```

**What this means:**
- **Feeds OK: 87** - Successfully downloaded posts from 87 blogs
- **Feeds errored: 5** - 5 blogs had issues (timeout, offline, or RSS feed problems) - this is normal
- **New posts: 2363** - Found 2,363 blog posts total
- **Skipped (duplicate): 0** - No duplicates (since this is your first fetch)

**What just happened?**
The tool visited each blog's RSS feed (a machine-readable list of recent posts) and saved the post title, description, link, and date to a local SQLite database (a simple file-based database stored in `data/blogs.db`).

**Tip:** Some blogs are slow or temporarily down. Errors are normal. 85-90 successful fetches is typical.

---

### Use Case 2: Check your database

**What you'll learn:** How to see what data you've collected

**Command:**
```bash
hn-intel status
```

**What you'll see:**
```
Blogs: 92
Posts: 2363
Last fetch: 2026-02-09 22:23:15
```

**What this means:**
- **Blogs: 92** - The database knows about 92 blogs
- **Posts: 2363** - You've collected 2,363 blog posts
- **Last fetch** - The last time you ran `hn-intel fetch`

**What just happened?**
The tool read the database file (`data/blogs.db`) and counted how many blogs and posts are stored. Think of this as checking your inventory.

**Use this command:**
- Before running analysis (to make sure you have data)
- After fetching (to see if new posts were added)

---

### Use Case 3: Discover trending topics

**What you'll learn:** What topics are "heating up" across tech blogs

**Command:**
```bash
hn-intel analyze
```

**What happens:**
The tool runs three types of analysis:
1. **Trend analysis** - identifies emerging topics
2. **Network analysis** - finds citation patterns between blogs
3. **Clustering** - groups similar blogs together

This takes **30-60 seconds**.

**What you'll see:**
```
Computing trends...
  Periods: 157
  Emerging topics: 100
Extracting citations...
  Citations: 30
  Graph nodes: 92
  Graph edges: 30
Clustering blogs...
  Blogs clustered: 88
  Clusters: 8

Top emerging topics:
  agents (43.36x acceleration)
  silicon (32.77x acceleration)
  training (31.14x acceleration)
  claude (24.44x acceleration)
  card (19.46x acceleration)

Top blogs by PageRank:
  mitchellh.com (PR: 0.0380)
  matklad.github.io (PR: 0.0357)
  buttondown.com/hillelwayne (PR: 0.0312)
  simonwillison.net (PR: 0.0291)
  righto.com (PR: 0.0195)

Analysis complete.
```

**What this means:**

**Trending topics:**
- **agents (43.36x acceleration)** - The word "agents" appears 43 times more often in recent posts than in older posts. This means AI agents are a hot topic right now.
- The higher the "acceleration", the more the topic is trending upward.

**Top blogs by PageRank:**
- **PageRank** is a score (0 to 1) that measures how "important" a blog is based on how many other blogs link to it. Higher = more influential.
- These are the most-cited blogs in the network.

**What just happened?**
The tool analyzed all 2,363 posts to find patterns:
- It split posts into time periods (months) and counted keyword frequencies
- It extracted URLs from posts to find when blogs link to each other
- It used machine learning to group blogs with similar content

---

### Use Case 4: Generate your first report

**What you'll learn:** How to create detailed reports you can read later

**Command:**
```bash
hn-intel report
```

**What happens:**
This runs the same analysis as `hn-intel analyze`, plus surfaces project ideas from pain signals, then saves **9 detailed report files** to the `output/` folder.

This takes **30-60 seconds**.

**What you'll see:**
```
Running analysis...
Surfacing project ideas...
Generating reports...

Reports written to output/:
  output/summary.md
  output/trends.md
  output/trends.json
  output/network.md
  output/network.json
  output/clusters.md
  output/clusters.json
  output/ideas.md
  output/ideas.json
```

**What this means:**
Nine files were created in the `output/` folder:
- `.md` files are Markdown (human-readable text files)
- `.json` files are JSON (machine-readable data files)

**What just happened?**
The tool ran the full analysis and wrote the results to files. You can now open these files in any text editor and explore the data.

**Next step:** Open `output/summary.md` in a text editor.

**What you'll see in summary.md:**
```markdown
# HN Blog Intelligence Summary Report

## Dataset Overview

- **Blogs**: 92
- **Posts**: 2363
- **Date range**: 2020-01-01 to 2026-02-10
- **Periods analyzed**: 157

## Top Emerging Topics

| Keyword    | Acceleration   |   Recent Score |
|------------|----------------|----------------|
| agents     | 43.36x         |       0.021446 |
| silicon    | 32.77x         |       0.009966 |
| training   | 31.14x         |       0.008882 |
...
```

This file gives you a bird's-eye view of the analysis. See [Part 3](#part-3-understanding-the-output-files) for a detailed explanation of each section.

---

### Use Case 5: Find what tech bloggers are writing about AI

**What you'll learn:** How to search for specific topics in the data

**Command:**
No command - just open a file.

**Step 1:** Open `output/trends.json` in a text editor.

**Step 2:** Use your editor's "Find" function (`Ctrl+F` or `Cmd+F`) and search for `"claude"`.

**What you'll see:**
```json
"claude": 0.015761,
```

This means "claude" (the AI assistant) has a TF-IDF score of 0.0158 in the most recent period.

**Step 3:** Scroll up a bit. You'll see data organized by time period:
```json
{
  "periods": {
    "2026-02": {
      "claude": 0.015761,
      "agents": 0.021446,
      "llm": 0.010143,
      ...
    },
    "2026-01": {
      "claude": 0.008123,
      "agents": 0.012456,
      ...
    }
  }
}
```

**What this means:**
The score for "claude" increased from 0.008 (January) to 0.016 (February), showing growing interest.

**What just happened?**
You manually explored the raw data file. JSON files are structured data - harder to read than Markdown, but useful for detailed exploration.

**Try searching for:** `"ai"`, `"agents"`, `"llm"`, `"python"`, `"rust"`, or any tech term you're curious about.

---

### Use Case 6: Discover which blogs cite each other

**What you'll learn:** Who's linking to whom in the tech blogosphere

**Step 1:** Open `output/network.md` in a text editor.

**What you'll see:**
```markdown
# Network Analysis Report

## Graph Statistics

- **Nodes (blogs)**: 92
- **Edges (citations)**: 30
- **Density**: 0.003583

## Top Blogs by PageRank

| Blog                               |   PageRank |   In-Degree |   Out-Degree |
|------------------------------------|------------|-------------|--------------|
| mitchellh.com                      |   0.037951 |           2 |            0 |
| matklad.github.io                  |   0.035738 |           1 |            0 |
| buttondown.com/hillelwayne         |   0.031158 |           3 |            1 |
| simonwillison.net                  |   0.029136 |           5 |            1 |
...
```

**What this means:**

**Graph Statistics:**
- **Nodes**: Each blog is a "node" in the network
- **Edges**: Each citation (blog A links to blog B) is an "edge"
- **Density**: How interconnected the network is (0 = no links, 1 = everyone links to everyone). 0.0036 is very sparse - blogs mostly don't link to each other.

**PageRank:**
Think of PageRank like a "popularity vote". If important blogs link to you, your PageRank goes up.
- **mitchellh.com** has the highest PageRank (0.038) - it's the most influential blog in this network.

**In-Degree:**
How many blogs link TO this blog.
- **simonwillison.net** has an in-degree of 5 - meaning 5 other blogs linked to it.

**Out-Degree:**
How many blogs this blog links OUT to.
- **simonwillison.net** has an out-degree of 1 - it linked to 1 other blog.

**What just happened?**
The tool scanned all blog posts for URLs, identified which blogs link to which, and calculated influence scores.

**PageRank in plain English:** Imagine a blog is a person at a party. PageRank measures how many people are walking over to talk to them. If lots of people (especially popular people) want to talk to you, your PageRank is high.

---

### Use Case 7: Find blogs similar to one you like

**What you'll learn:** Discover new blogs based on content similarity

**Step 1:** Open `output/clusters.json` in a text editor.

**Step 2:** Use Find (`Ctrl+F` or `Cmd+F`) to search for a blog you know. Try `"simonwillison.net"`.

**What you'll see:**
```json
{
  "cluster_id": 1,
  "label": "code, like, software, model, use",
  "blogs": [
    "antirez.com",
    "blog.pixelmelt.dev",
    "buttondown.com/hillelwayne",
    ...
    "simonwillison.net",
    ...
  ]
}
```

**What this means:**
- **simonwillison.net** is in cluster 1
- This cluster is labeled "code, like, software, model, use" (the most common words in posts from these blogs)
- All the other blogs in this list write about similar topics

**What just happened?**
The tool used a machine learning algorithm called **K-means clustering** to group blogs with similar content. Think of it like organizing books in a library - blogs about similar topics get grouped together.

**How to use this:**
If you like one blog in a cluster, try reading the others in the same cluster - they probably cover topics you'll enjoy.

**Example:** If you like Simon Willison's blog (AI, Python, software), you might also like:
- antirez.com
- matklad.github.io
- lucumr.pocoo.org

---

### Use Case 8: Explore blog topic clusters

**What you'll learn:** See how blogs are grouped by topic

**Step 1:** Open `output/clusters.md` in a text editor.

**What you'll see:**
```markdown
# Blog Cluster Report

## Cluster Assignments

### Cluster 0: history, post, intel, numbers, number

- abortretry.fail
- johndcook.com
- tedium.co

### Cluster 1: code, like, software, model, use

- antirez.com
- blog.pixelmelt.dev
- buttondown.com/hillelwayne
- simonwillison.net
...

### Cluster 2: nixos, nix, https, code, text

- borretti.me
- mitchellh.com
- pluralistic.net
...
```

**What this means:**

**Cluster 0: history, post, intel, numbers, number**
These blogs focus on tech history, retro computing, and interesting numbers/facts.

**Cluster 1: code, like, software, model, use**
These blogs focus on software development, AI models, and coding practices. This is the largest cluster (23 blogs).

**Cluster 2: nixos, nix, https, code, text**
These blogs focus on NixOS (a Linux distribution), infrastructure, and technical deep-dives.

**What just happened?**
The tool used **TF-IDF** (Term Frequency-Inverse Document Frequency) to identify what makes each blog unique, then grouped blogs with similar "fingerprints" together.

**TF-IDF in plain English:** It's like a word cloud, but smarter. Common words like "the" and "and" are ignored. Unique words like "nixos" get higher scores. Blogs with similar high-scoring words get clustered together.

---

### Use Case 9: Discover project ideas from blog pain signals

**What you'll learn:** How to surface actionable project ideas from what bloggers wish existed

**Command:**
```bash
hn-intel ideas
```

**What happens:**
The tool scans all blog posts for "pain-point language" — phrases where bloggers express wishes, frustrations, gaps, or difficulties. It then scores each signal by trend momentum, blog authority, breadth across blogs, and recency, and clusters related signals into coherent project idea themes.

This takes **30-60 seconds**.

**What you'll see:**
```
Surfacing project ideas...
Found 15 project ideas:

  1. Wasm, Tools, Developer, Debugging, Profiling
     Impact: 0.72 | Blogs: 4 | Signals: 7
     "I wish there was a decent WASM profiler that actually works..."
     Sources: simonwillison.net, xeiaso.net, fasterthanli.me, matklad.github.io

  2. Api, Testing, Documentation, Workflow
     Impact: 0.65 | Blogs: 3 | Signals: 5
     "It's frustratingly hard to test APIs when documentation is outdated..."
     Sources: blog.codinghorror.com, antirez.com, lucumr.pocoo.org

  ...
```

**What this means:**
- **Impact score (0 to 1):** Higher = stronger signal. Combines trend momentum, blog authority, breadth, and recency.
- **Blogs:** How many distinct blogs expressed this pain point. More blogs = more validation.
- **Signals:** Total number of pain expressions found for this idea.
- **Quote:** A representative sentence from a blog post.
- **Sources:** The blogs that contributed to this idea.

**What just happened?**
The tool used regular expressions to find pain-point phrases (e.g., "I wish", "hard to", "no good tool for"), then used TF-IDF and agglomerative clustering to group related complaints into coherent project ideas. Each idea is ranked by how well it aligns with emerging trends and influential blogs.

**Save results to files:**
```bash
hn-intel ideas --output-dir output
```
This generates `output/ideas.md` and `output/ideas.json`.

**View the detailed report:**
Open `output/ideas.md` for justifications, source attribution, and key quotes for each idea.

---

### Use Case 10: Analyze trends by week instead of month

**What you'll learn:** How to adjust the time granularity of trend analysis

**Command:**
```bash
hn-intel report --period week --output-dir output_weekly/
```

**What this does:**
- `--period week` tells the tool to group posts by week instead of month
- `--output-dir output_weekly/` saves reports to a different folder so you don't overwrite the monthly reports

**What you'll see:**
```
Running analysis...
Generating reports...

Reports written to output_weekly/:
  output_weekly/summary.md
  output_weekly/trends.md
  ...
```

**What just happened?**
Instead of grouping posts by month (January, February, etc.), the tool grouped them by week (Week 1, Week 2, etc.). This gives you finer-grained trend detection.

**When to use weekly vs monthly:**
- **Monthly:** Better for long-term trends (what topics are growing over 6-12 months)
- **Weekly:** Better for detecting recent spikes (what's hot this week vs last week)

**Next step:** Compare `output/trends.md` (monthly) to `output_weekly/trends.md` (weekly). Look for differences in what's trending.

---

### Use Case 11: Update your data with fresh posts

**What you'll learn:** How to keep your data current

**Command:**
```bash
hn-intel fetch
```

(Yes, the same command as Use Case 1!)

**What you'll see (if you run this the next day):**
```
Fetching 92 feeds...
  [####################################]  100%
Feeds OK: 88
Feeds errored: 4
New posts: 15
Skipped (duplicate): 2348
```

**What this means:**
- **New posts: 15** - Found 15 new blog posts since your last fetch
- **Skipped (duplicate): 2348** - Skipped 2,348 posts that were already in the database

**What just happened?**
The tool fetched all RSS feeds again, but only added *new* posts. It detected duplicates by checking the post URL - if a post with that URL already exists, it skips it.

**How often should you fetch?**
- **Daily:** If you want to stay current with the latest posts
- **Weekly:** If you just want to track trends over time
- **Before each analysis:** Always fetch before running `hn-intel report` to ensure you have the latest data

**Tip:** After fetching, run `hn-intel status` to see your updated post count.

---

## Part 3: Understanding the Output Files

When you run `hn-intel report`, you get 9 files. Here's what each one contains.

---

### summary.md - Your one-page overview

**What it is:** A single-page summary of all analysis results

**Sections:**

#### 1. Dataset Overview
```markdown
- **Blogs**: 92
- **Posts**: 2363
- **Date range**: 2020-01-01 to 2026-02-10
- **Periods analyzed**: 157
```

**What it tells you:** How much data you're working with and the time span it covers.

#### 2. Top Emerging Topics
```markdown
| Keyword    | Acceleration   |   Recent Score |
|------------|----------------|----------------|
| agents     | 43.36x         |       0.021446 |
| silicon    | 32.77x         |       0.009966 |
```

**What it tells you:** The hottest trending topics right now.

**Acceleration:** How much more frequently this word appears now vs historically. 43.36x means it appears 43 times more often.

**Recent Score:** The TF-IDF score in the most recent time period. Higher = more important/unique to recent posts.

#### 3. Most-Cited Blogs (by PageRank)
```markdown
| Blog                  |   PageRank |   In-Degree |   Out-Degree |
|-----------------------|------------|-------------|--------------|
| mitchellh.com         |   0.037951 |           2 |            0 |
```

**What it tells you:** Which blogs are most influential in the network.

#### 4. Blog Clusters
```markdown
|   Cluster | Label                                 |   Blog Count |
|-----------|---------------------------------------|--------------|
|         0 | history, post, intel, numbers, number |            3 |
```

**What it tells you:** How blogs are grouped by topic.

#### 5. Top Project Ideas
```markdown
|   Rank | Idea                               |   Impact |   Blogs |   Signals |
|--------|------------------------------------|----------|---------|-----------|
|      1 | Wasm, Tools, Developer, Debugging  |     0.72 |       4 |         7 |
```

**What it tells you:** The highest-impact project opportunities based on pain signals from blog content. Higher impact = stronger signal combining trends, authority, breadth, and recency.

---

### trends.md / trends.json - Topic trend details

**What it is:** A ranked list of all trending keywords

**Markdown (.md) version:**
Human-readable table:
```markdown
| Keyword      | Acceleration   |   Recent Score |   Historical Avg |
|--------------|----------------|----------------|------------------|
| agents       | 43.36x         |       0.021446 |         0.000495 |
```

**JSON (.json) version:**
Machine-readable data:
```json
{
  "periods": {
    "2026-02": {
      "agents": 0.021446,
      "silicon": 0.009966,
      ...
    },
    "2026-01": {
      "agents": 0.012456,
      ...
    }
  }
}
```

**How to read this:**

**Acceleration:** Recent Score ÷ Historical Average
- If a word used to appear with score 0.0005 and now appears with score 0.021, that's 42x acceleration.

**Recent Score:** TF-IDF score in the most recent period.

**Historical Avg:** Average TF-IDF score across all previous periods.

**When to use:**
- Markdown: Quick scan of top trends
- JSON: Detailed exploration, building your own charts

---

### network.md / network.json - Citation network details

**What it is:** Information about which blogs link to which

**Markdown (.md) version:**
```markdown
## Graph Statistics

- **Nodes (blogs)**: 92
- **Edges (citations)**: 30
- **Density**: 0.003583

## Top Blogs by PageRank

| Blog                  |   PageRank |   In-Degree |   Out-Degree |
|-----------------------|------------|-------------|--------------|
| mitchellh.com         |   0.037951 |           2 |            0 |
```

**JSON (.json) version:**
```json
{
  "graph_stats": {
    "nodes": 92,
    "edges": 30,
    "density": 0.003583
  },
  "centrality": {
    "mitchellh.com": {
      "pagerank": 0.037951,
      "in_degree": 2,
      "out_degree": 0,
      "betweenness": 0.0
    },
    ...
  }
}
```

**Key metrics explained:**

**PageRank (0 to 1):** Influence score based on incoming links. Higher = more influential.

**In-Degree:** How many blogs link TO this blog. Higher = more cited.

**Out-Degree:** How many blogs this blog links TO. Higher = more "generous" with citations.

**Betweenness:** How often this blog appears on the shortest path between two other blogs. High betweenness = "bridge" between communities.

**When to use:**
- Markdown: See the top influential blogs
- JSON: Explore the full network data, see all connections

---

### clusters.md / clusters.json - Blog grouping details

**What it is:** Which blogs are grouped together by topic similarity

**Markdown (.md) version:**
```markdown
### Cluster 0: history, post, intel, numbers, number

- abortretry.fail
- johndcook.com
- tedium.co

### Cluster 1: code, like, software, model, use

- antirez.com
- simonwillison.net
...
```

**JSON (.json) version:**
```json
{
  "clusters": [
    {
      "cluster_id": 0,
      "label": "history, post, intel, numbers, number",
      "blogs": [
        "abortretry.fail",
        "johndcook.com",
        "tedium.co"
      ]
    },
    ...
  ],
  "similarity_matrix": {
    "abortretry.fail": {
      "johndcook.com": 0.234,
      "tedium.co": 0.189,
      ...
    }
  }
}
```

**What the numbers mean:**

**Cluster label:** The 5 most common words in posts from blogs in this cluster.

**Similarity matrix (in JSON):** A score (0 to 1) showing how similar two blogs are.
- 0.0 = completely different
- 1.0 = identical
- 0.5 = moderately similar

**When to use:**
- Markdown: Discover new blogs similar to ones you like
- JSON: See exact similarity scores between any two blogs

---

### ideas.md / ideas.json - Project idea details

**What it is:** Ranked project ideas derived from pain signals in blog content

**Markdown (.md) version:**
```markdown
## 1. Wasm, Tools, Developer, Debugging, Profiling
**Impact Score**: 0.72 | **Blogs**: 4 | **Signals**: 7

### Justification

4 blogs independently describe this pain point, including simonwillison.net,
xeiaso.net, fasterthanli.me. Pain signals span 3 frustration, 2 gap, 2 wish
categories. Related emerging keywords: wasm, tools, debugging. High composite
impact score suggests strong unmet demand.

### Sources

| Blog                          | Post              | Date       | Pain Type   |
|-------------------------------|-------------------|------------|-------------|
| [simonwillison.net](url)      | WASM Pain Points  | 2026-01-15 | frustration |
| [xeiaso.net](url)             | Tools We Need     | 2026-01-20 | wish        |

### Key Quotes

> "I wish there was a decent WASM profiler that actually works" — **simonwillison.net**
```

**JSON (.json) version:**
```json
{
  "ideas": [
    {
      "idea_id": 0,
      "label": "wasm, tools, developer, debugging, profiling",
      "impact_score": 0.72,
      "justification": "4 blogs independently describe this pain point...",
      "keywords": ["wasm", "tools", "developer"],
      "signal_count": 7,
      "blog_count": 4,
      "pain_type_breakdown": {"frustration": 3, "gap": 2, "wish": 2},
      "representative_quote": "I wish there was a decent WASM profiler...",
      "sources": [...]
    }
  ]
}
```

**Key concepts explained:**

**Impact Score (0 to 1):** A composite score combining:
- **Trend momentum (35%)**: Does this pain relate to an accelerating topic?
- **Authority (25%)**: Is the source blog influential (high PageRank)?
- **Breadth (25%)**: How many distinct blogs express this pain?
- **Recency (15%)**: How recently was this pain expressed?

**Pain types:** The tool detects six categories:
- **Wish**: "I wish there was...", "someone should build..."
- **Frustration**: "frustrating", "drives me crazy"
- **Gap**: "no good tool for...", "missing", "lacking"
- **Difficulty**: "hard to...", "struggle with..."
- **Broken**: "buggy", "unreliable", "constantly breaks"
- **Opportunity**: "ripe for disruption", "room for..."

**When to use:**
- Markdown: Read justifications and explore idea sources
- JSON: Programmatic access for building dashboards or filtering ideas

---

## Part 4: Command Reference

Here's every command this tool supports.

---

### hn-intel fetch

**Purpose:** Download blog posts from RSS feeds

**Usage:**
```bash
hn-intel fetch [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--opml` | `docs/hn-blogs.opml` | Path to the OPML file listing blog feeds |
| `--timeout` | `30` | How long to wait for each feed (in seconds) |
| `--delay` | `0.5` | Delay between requests (in seconds) |

**Examples:**

```bash
# Basic fetch (uses defaults)
hn-intel fetch

# Fetch with a longer timeout for slow blogs
hn-intel fetch --timeout 60

# Fetch with a longer delay (to be polite to servers)
hn-intel fetch --delay 1.0

# Use a different OPML file
hn-intel fetch --opml my-blogs.opml
```

**When to use:**
- First time setting up (to download initial data)
- Daily/weekly to get new posts
- Before running analysis (to ensure fresh data)

---

### hn-intel status

**Purpose:** Check how much data you've collected

**Usage:**
```bash
hn-intel status
```

**No options.** Just run it.

**Output:**
```
Blogs: 92
Posts: 2363
Last fetch: 2026-02-09 22:23:15
```

**When to use:**
- After fetching (to see if it worked)
- Before analyzing (to check you have data)
- Anytime you're curious about your dataset

---

### hn-intel analyze

**Purpose:** Run analysis and print a summary to the terminal

**Usage:**
```bash
hn-intel analyze [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--max-features` | `500` | How many words to track for TF-IDF analysis |
| `--n-clusters` | `8` | How many blog clusters to create |
| `--period` | `month` | Time period for trends (`month` or `week`) |

**Examples:**

```bash
# Basic analysis (uses defaults)
hn-intel analyze

# Track more words (slower, but more detailed)
hn-intel analyze --max-features 1000

# Create fewer clusters (for simpler grouping)
hn-intel analyze --n-clusters 5

# Analyze weekly trends instead of monthly
hn-intel analyze --period week

# Combine options
hn-intel analyze --period week --n-clusters 6 --max-features 750
```

**When to use:**
- Quick check of trends without generating files
- Testing different parameters before running full reports

**Difference from `report`:** This just prints to the terminal. Use `report` to save files.

---

### hn-intel ideas

**Purpose:** Surface high-impact project ideas from blog pain signals

**Usage:**
```bash
hn-intel ideas [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--max-features` | `500` | How many words to track for TF-IDF analysis |
| `--top-n` | `20` | Maximum number of ideas to surface |
| `--period` | `month` | Time period for trends (`month` or `week`) |
| `--output-dir` | None | Optional directory to save ideas.md and ideas.json |

**Examples:**

```bash
# Surface top 20 ideas (print to terminal)
hn-intel ideas

# Surface top 10 ideas
hn-intel ideas --top-n 10

# Save ideas to files
hn-intel ideas --output-dir output

# Use weekly trends for scoring
hn-intel ideas --period week --top-n 15 --output-dir output
```

**When to use:**
- Discovering what tools and solutions developers are wishing for
- Finding project ideas backed by real pain points from influential blogs
- Generating a ranked list of opportunities to explore

**Difference from `report`:** The `ideas` command only surfaces ideas (not trends, network, or clusters). Use `report` to generate all reports at once.

---

### hn-intel report

**Purpose:** Run analysis and save results to files

**Usage:**
```bash
hn-intel report [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir` | `output` | Where to save report files |
| `--max-features` | `500` | How many words to track for TF-IDF analysis |
| `--n-clusters` | `8` | How many blog clusters to create |
| `--period` | `month` | Time period for trends (`month` or `week`) |

**Examples:**

```bash
# Basic report (uses defaults)
hn-intel report

# Save to a different folder
hn-intel report --output-dir my-reports

# Weekly trends with more detailed analysis
hn-intel report --period week --max-features 1000

# Simplified clustering
hn-intel report --n-clusters 5

# Separate weekly and monthly reports
hn-intel report --period week --output-dir output_weekly
hn-intel report --period month --output-dir output_monthly
```

**When to use:**
- Generating reports to share with others
- Keeping a historical record of trends
- Creating multiple analyses with different parameters

---

## Part 5: FAQ & Troubleshooting

---

### Installation & Setup

**Q: I get "python: command not found"**

**A:** Python is not installed or not in your system PATH.
- Install Python from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"
- Restart your terminal after installing

---

**Q: I get "pip: command not found"**

**A:** Pip comes with Python, but sometimes needs to be called differently.
- Try `python -m pip install -e ".[dev]"` instead of `pip install -e ".[dev]"`

---

**Q: Virtual environment activation doesn't work**

**Windows users:** Use `.\venv\Scripts\activate` (with a period at the start)

**PowerShell users:** You may need to enable script execution first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Mac/Linux users:** Make sure you use `source`, not just the path:
```bash
source .venv/bin/activate
```

---

**Q: I see "(.venv)" but `hn-intel` command doesn't work**

**A:** The installation may have failed. Try reinstalling:
```bash
pip install -e ".[dev]"
```

Check for error messages. If you see "Successfully installed", try again.

---

### Fetching Data

**Q: I got a timeout error**

**A:** Some blogs are slow or temporarily down. This is normal.
- If 80+ feeds succeed, you're fine.
- Try increasing the timeout: `hn-intel fetch --timeout 60`
- Try again later - the blog might be down temporarily

---

**Q: I see 0 new posts**

**A:** This means you already have all available posts.
- If this is your first fetch, the blogs may not have RSS feeds or the feeds are empty.
- If you fetched recently, just wait - blogs don't post every hour.
- Run `hn-intel status` to confirm you have posts in the database.

---

**Q: Feeds errored increased from 5 to 15**

**A:** Blogs go offline, change domains, or block automated requests.
- Normal fluctuation: 5-10 errors is typical
- Concerning: 30+ errors means something might be wrong with your internet connection
- Check the OPML file (`docs/hn-blogs.opml`) - some blog URLs may be outdated

---

**Q: Can I add my own blogs to track?**

**A:** Yes! Edit `docs/hn-blogs.opml` in a text editor.

Add a new line in this format:
```xml
<outline text="Blog Name" title="Blog Name" type="rss" xmlUrl="https://example.com/feed.xml" htmlUrl="https://example.com"/>
```

Then run `hn-intel fetch` to add posts from the new blog.

---

### Analysis & Reports

**Q: Analysis is slow (takes 2+ minutes)**

**A:** Try reducing complexity:
```bash
hn-intel analyze --max-features 250 --n-clusters 5
```

**Why this helps:**
- `--max-features 250` tracks fewer words (default is 500)
- `--n-clusters 5` creates fewer clusters (default is 8)

---

**Q: What is TF-IDF?**

**A:** **TF-IDF** = Term Frequency-Inverse Document Frequency

**In plain English:**
- **Term Frequency (TF):** How often a word appears in a document (blog post)
- **Inverse Document Frequency (IDF):** How rare the word is across all documents
- **TF-IDF:** Multiplies TF × IDF to find important, unique words

**Example:**
- The word "the" appears often (high TF) but in every post (low IDF) → low TF-IDF
- The word "nixos" appears often in a post (high TF) and rarely elsewhere (high IDF) → high TF-IDF

**Why it matters:** TF-IDF helps identify what makes each post unique, filtering out common words.

---

**Q: What is PageRank?**

**A:** A score (0 to 1) that measures a blog's influence based on citations.

**In plain English:**
Imagine a voting system where:
- Each blog "votes" for other blogs by linking to them
- Votes from important blogs count more than votes from unimportant blogs
- Your PageRank is calculated by how many votes you get and who they're from

**Created by Google's founders** to rank web pages. We use it to rank blogs.

---

**Q: What is K-means clustering?**

**A:** A machine learning algorithm that groups similar things together.

**In plain English:**
1. The computer represents each blog as a point in multi-dimensional space (based on the words they use)
2. It randomly places 8 "cluster centers" in that space
3. It assigns each blog to the nearest cluster center
4. It moves each cluster center to the average position of its blogs
5. It repeats steps 3-4 until the clusters stabilize

**Result:** Blogs with similar content end up in the same cluster.

---

**Q: What does "acceleration" mean?**

**A:** How much faster a topic is trending now vs historically.

**Formula:**
```
Acceleration = Recent Score ÷ Historical Average
```

**Example:**
- "agents" has a recent score of 0.021 and historical average of 0.0005
- Acceleration = 0.021 ÷ 0.0005 = 42x
- This means "agents" appears 42 times more often now than it used to

---

**Q: Why are some clusters bigger than others?**

**A:** K-means doesn't create equal-sized clusters. It groups blogs by similarity, not count.
- Cluster 1 might have 23 blogs (all about software development)
- Cluster 3 might have 2 blogs (both about Google-specific topics)

This is normal and expected.

---

**Q: How often should I fetch new data?**

**A:** Depends on your goal:

| Goal | Frequency |
|------|-----------|
| Daily newsletter | Fetch daily |
| Weekly trend report | Fetch weekly |
| Monthly deep-dive | Fetch monthly |
| Historical research | Fetch once, then whenever you need updates |

**Tip:** Blogs don't post every day. Even if you fetch daily, you might only see 10-20 new posts.

---

**Q: Can I export data to Excel/Google Sheets?**

**A:** Not directly, but you can:
1. Open the `.json` files
2. Use an online JSON-to-CSV converter (search "JSON to CSV")
3. Import the CSV into Excel/Sheets

**Alternative:** Copy tables from `.md` files and paste into Excel - they're already formatted as tables.

---

**Q: The trends seem wrong / I expected a different topic to be trending**

**A:** A few reasons this might happen:
1. **Timing:** You may have just missed a topic spike (fetch more often)
2. **Sample size:** 92 blogs is curated but small - not all trends will appear
3. **TF-IDF bias:** Rare words score higher than common ones. "nixos" might rank higher than "python" because it's rarer.
4. **Filtering:** Very common words are filtered out. "AI" might not appear if it's mentioned in almost every post.

**Tip:** Use `--max-features 1000` to track more words.

---

**Q: Can I delete old data and start fresh?**

**A:** Yes. Delete the database file:
```bash
rm data/blogs.db
```
(On Windows: `del data\blogs.db`)

Then run `hn-intel fetch` to rebuild from scratch.

---

**Q: Where is the data stored?**

**A:** In `data/blogs.db` - a SQLite database file.

**What is SQLite?** A simple, file-based database. No server needed. The entire database is one file.

**Can I explore it?** Yes, using tools like:
- [DB Browser for SQLite](https://sqlitebrowser.org/) (free, GUI)
- `sqlite3` command-line tool (comes with Python)

---

**Q: This tool uses machine learning - do I need a GPU?**

**A:** No. The algorithms used (TF-IDF, K-means, PageRank) are classical ML, not deep learning. They run fast on a CPU.

You don't need a GPU, cloud account, or powerful computer. A regular laptop is fine.

---

**Q: Can I run this on a Raspberry Pi?**

**A:** Yes, if you have Python 3.10+ installed. It might be slower (2-3 minutes for analysis instead of 30-60 seconds), but it works.

---

**Q: I want to learn more about how this works**

**A:** Great! Here are the key concepts to research:

| Concept | What to search for |
|---------|-------------------|
| RSS feeds | "What is an RSS feed" |
| TF-IDF | "TF-IDF explained" |
| PageRank | "PageRank algorithm explained" |
| K-means clustering | "K-means clustering tutorial" |
| Graph theory | "Introduction to graph theory" |
| SQLite | "SQLite database tutorial" |

---

### Error Messages

**Q: "Database is locked"**

**A:** Another process is using the database.
- Close any other terminals running `hn-intel` commands
- Close any database browser tools (DB Browser for SQLite, etc.)
- Restart the command

---

**Q: "Permission denied" when activating virtual environment**

**A (Windows PowerShell users):** Enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**A (Mac/Linux users):** Make sure you're using `source`:
```bash
source .venv/bin/activate
```

---

**Q: "No module named 'hn_intel'"**

**A:** The virtual environment isn't activated or installation failed.
1. Make sure you see `(.venv)` at the start of your prompt
2. If not, activate it: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac/Linux)
3. If still broken, reinstall: `pip install -e ".[dev]"`

---

**Q: "UnicodeDecodeError" when generating reports**

**A:** A blog post has unusual characters. This is rare.
- Try again - it might be a one-time network glitch
- If it persists, file a bug report with the error message

---

### Getting Help

**Q: I have a question not answered here**

**A:** Check the project documentation:
- Read `docs/findings.md` for background on the project
- Check the GitHub repository (if publicly available)
- File an issue describing your problem

**When asking for help, include:**
1. What command you ran
2. What you expected to happen
3. What actually happened (error message)
4. Your Python version (`python --version`)
5. Your operating system (Windows, Mac, Linux)

---

## Appendix: Glossary

**Command Line / Terminal:** A text-based interface for running programs by typing commands.

**RSS Feed:** A machine-readable file that lists a blog's recent posts (title, link, date, summary).

**OPML:** An XML file format that lists multiple RSS feeds. Used to organize blog subscriptions.

**SQLite:** A simple, file-based database. No server required.

**Virtual Environment:** An isolated Python environment for a specific project. Keeps dependencies separate.

**pip:** Python's package installer. Downloads and installs Python libraries.

**TF-IDF:** A score (0 to 1) that measures how important a word is to a document. Filters out common words.

**PageRank:** A score (0 to 1) that measures a blog's influence based on incoming links.

**K-means Clustering:** A machine learning algorithm that groups similar items together.

**Acceleration:** How much faster a topic is trending now vs historically (Recent Score ÷ Historical Avg).

**In-Degree:** How many blogs link TO a blog.

**Out-Degree:** How many blogs a blog links TO.

**Betweenness Centrality:** How often a blog appears on the shortest path between two other blogs. High = "bridge" between communities.

**Cosine Similarity:** A score (0 to 1) that measures how similar two blogs are based on their content. 1 = identical, 0 = completely different.

**Node:** In graph theory, a point in a network (in this tool, a blog).

**Edge:** In graph theory, a connection between two nodes (in this tool, a citation).

**JSON:** JavaScript Object Notation - a text format for structured data. Machine-readable.

**Markdown:** A simple text format for writing documents with basic formatting. Human-readable.

---

## Conclusion

You now know how to:
- Install and set up the HN Blog Intelligence Platform
- Fetch blog posts from 92 tech blogs
- Run analysis to discover trending topics, influential blogs, and blog clusters
- Surface project ideas from pain signals in blog content
- Generate detailed reports
- Interpret the output files
- Troubleshoot common issues

**Next steps:**
1. Run `hn-intel fetch` to download data
2. Run `hn-intel report` to generate your first analysis
3. Open `output/summary.md` and explore the results
4. Set up a weekly reminder to fetch new data

**Happy exploring!**

---

*This guide was written for the HN Blog Intelligence Platform v0.1.0. If you find errors or have suggestions, please submit an issue.*
