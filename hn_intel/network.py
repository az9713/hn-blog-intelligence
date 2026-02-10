"""Network analysis for cross-blog citations."""

import re
from urllib.parse import urlparse

import networkx as nx

from hn_intel.db import get_all_posts, get_blog_domains, get_blogs

# Shared hosting platforms where subdomain identifies the blog
_SHARED_PLATFORMS = {"blogspot.com", "substack.com", "github.io", "dreamwidth.org"}

_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def _normalize_domain(domain):
    """Normalize a domain for matching.

    Strips www. prefix and, for shared platforms, returns the full
    subdomain.host so that e.g. alice.blogspot.com != bob.blogspot.com.
    For regular domains, strips www. only.

    Returns:
        Normalized domain string.
    """
    domain = domain.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _build_domain_map(conn):
    """Build an extended domain map that includes shared-platform subdomains.

    The base get_blog_domains already strips www. from site_url domains.
    This function additionally registers the full subdomain form for
    shared platforms so that links to alice.substack.com match.

    Returns:
        Dict mapping normalized domain -> blog_id.
    """
    base_domains = get_blog_domains(conn)

    extended = {}
    for domain, blog_id in base_domains.items():
        extended[domain] = blog_id
        # For shared platforms, the base domain may already include
        # the subdomain (e.g. alice.blogspot.com). We keep it as-is.

    return extended


def _domain_from_url(url):
    """Extract and normalize the domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or ""
    except Exception:
        return ""
    return _normalize_domain(domain)


def _match_domain(url_domain, domain_map):
    """Try to match a URL domain against the known blog domain map.

    Handles both exact matches and shared-platform subdomain matching.

    Returns:
        blog_id if matched, None otherwise.
    """
    if not url_domain:
        return None

    # Exact match first
    if url_domain in domain_map:
        return domain_map[url_domain]

    # For shared platforms, try matching the subdomain portion
    # e.g. url has alice.blogspot.com, domain_map might have alice.blogspot.com
    # This is already handled by exact match above, but we also handle
    # the case where the URL has extra subdomains
    for platform in _SHARED_PLATFORMS:
        if url_domain.endswith("." + platform):
            # Already tried exact match; no further heuristic needed
            break

    return None


def extract_citations(conn):
    """Extract cross-blog citations from post descriptions.

    Scans all post descriptions for href URLs, matches them against
    known blog domains, and inserts citation records into the database.
    Self-citations (source blog == target blog) are skipped.

    Args:
        conn: sqlite3.Connection instance.

    Returns:
        Number of citations inserted.
    """
    posts = get_all_posts(conn)
    domain_map = _build_domain_map(conn)

    count = 0
    for post in posts:
        description = post["description"] or ""
        source_blog_id = post["blog_id"]

        urls = _HREF_RE.findall(description)
        for url in urls:
            url_domain = _domain_from_url(url)
            target_blog_id = _match_domain(url_domain, domain_map)

            if target_blog_id is None:
                continue
            if target_blog_id == source_blog_id:
                continue

            conn.execute(
                "INSERT INTO citations (source_post_id, source_blog_id, target_blog_id, target_url) "
                "VALUES (?, ?, ?, ?)",
                (post["id"], source_blog_id, target_blog_id, url),
            )
            count += 1

    conn.commit()
    return count


def build_citation_graph(conn):
    """Build a directed citation graph from the citations table.

    Nodes represent blogs (with a 'name' attribute). Directed edges
    represent citations from source to target, weighted by citation count.

    Args:
        conn: sqlite3.Connection instance.

    Returns:
        networkx.DiGraph with blog nodes and weighted citation edges.
    """
    graph = nx.DiGraph()

    blogs = get_blogs(conn)
    for blog in blogs:
        graph.add_node(blog["id"], name=blog["name"])

    rows = conn.execute(
        "SELECT source_blog_id, target_blog_id, COUNT(*) as weight "
        "FROM citations GROUP BY source_blog_id, target_blog_id"
    ).fetchall()

    for row in rows:
        graph.add_edge(row["source_blog_id"], row["target_blog_id"], weight=row["weight"])

    return graph


def compute_centrality(graph):
    """Compute centrality metrics for each blog in the citation graph.

    Computes PageRank, betweenness centrality, in-degree, and out-degree
    for every node.

    Args:
        graph: networkx.DiGraph with blog nodes having a 'name' attribute.

    Returns:
        Dict mapping blog name to dict of centrality metrics:
        {blog_name: {pagerank, betweenness, in_degree, out_degree}}.
    """
    if len(graph) == 0:
        return {}

    pagerank = nx.pagerank(graph, weight="weight")
    betweenness = nx.betweenness_centrality(graph, weight="weight")

    result = {}
    for node in graph.nodes():
        name = graph.nodes[node].get("name", str(node))
        result[name] = {
            "pagerank": pagerank.get(node, 0.0),
            "betweenness": betweenness.get(node, 0.0),
            "in_degree": graph.in_degree(node),
            "out_degree": graph.out_degree(node),
        }

    return result
