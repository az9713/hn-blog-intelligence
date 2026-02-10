"""CLI entry point for HN Blog Intelligence."""

import click

from hn_intel.db import get_connection, init_db


@click.group()
def main():
    """HN Blog Intelligence Platform."""
    pass


@main.command()
@click.option("--opml", default="docs/hn-blogs.opml", help="Path to OPML file.")
@click.option("--timeout", default=30, type=int, help="Request timeout in seconds.")
@click.option("--delay", default=0.5, type=float, help="Delay between feed requests.")
def fetch(opml, timeout, delay):
    """Fetch all RSS feeds and store posts."""
    from hn_intel.fetcher import fetch_all_feeds

    conn = get_connection()
    init_db(conn)
    summary = fetch_all_feeds(conn, opml_path=opml, timeout=timeout, delay=delay)
    conn.close()

    click.echo(f"Feeds OK: {summary['feeds_ok']}")
    click.echo(f"Feeds errored: {summary['feeds_err']}")
    click.echo(f"New posts: {summary['new_posts']}")
    click.echo(f"Skipped (duplicate): {summary['skipped']}")


@main.command()
def status():
    """Show database status."""
    conn = get_connection()
    init_db(conn)

    blog_count = conn.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
    post_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    last_fetch = conn.execute(
        "SELECT MAX(last_fetched) FROM blogs"
    ).fetchone()[0]

    conn.close()

    click.echo(f"Blogs: {blog_count}")
    click.echo(f"Posts: {post_count}")
    click.echo(f"Last fetch: {last_fetch or 'never'}")


@main.command()
@click.option("--max-features", default=500, type=int, help="Max TF-IDF features.")
@click.option("--n-clusters", default=8, type=int, help="Number of blog clusters.")
@click.option("--period", default="month", type=click.Choice(["month", "week"]), help="Trend period.")
def analyze(max_features, n_clusters, period):
    """Run full analysis pipeline and print summary."""
    from hn_intel.analyzer import compute_trends, detect_emerging_topics
    from hn_intel.network import extract_citations, build_citation_graph, compute_centrality
    from hn_intel.clusters import compute_blog_vectors, cluster_blogs, compute_similarity_matrix

    conn = get_connection()
    init_db(conn)

    click.echo("Computing trends...")
    trends = compute_trends(conn, period=period)
    emerging = detect_emerging_topics(trends)
    click.echo(f"  Periods: {len(trends)}")
    click.echo(f"  Emerging topics: {len(emerging)}")

    click.echo("Extracting citations...")
    citation_count = extract_citations(conn)
    graph = build_citation_graph(conn)
    centrality = compute_centrality(graph)
    click.echo(f"  Citations: {citation_count}")
    click.echo(f"  Graph nodes: {graph.number_of_nodes()}")
    click.echo(f"  Graph edges: {graph.number_of_edges()}")

    click.echo("Clustering blogs...")
    blog_vectors, blog_names, vectorizer = compute_blog_vectors(conn, max_features=max_features)
    clusters = cluster_blogs(blog_vectors, blog_names, vectorizer, n_clusters=n_clusters)
    sim_matrix = compute_similarity_matrix(blog_vectors)
    click.echo(f"  Blogs clustered: {len(blog_names)}")
    click.echo(f"  Clusters: {len(clusters)}")

    if emerging:
        click.echo("\nTop emerging topics:")
        for e in emerging[:5]:
            click.echo(f"  {e['keyword']} ({e['acceleration']:.2f}x acceleration)")

    if centrality:
        top_blogs = sorted(centrality.items(), key=lambda x: x[1]["pagerank"], reverse=True)[:5]
        click.echo("\nTop blogs by PageRank:")
        for name, m in top_blogs:
            click.echo(f"  {name} (PR: {m['pagerank']:.4f})")

    conn.close()
    click.echo("\nAnalysis complete.")


@main.command()
@click.option("--output-dir", default="output", help="Directory for report files.")
@click.option("--max-features", default=500, type=int, help="Max TF-IDF features.")
@click.option("--n-clusters", default=8, type=int, help="Number of blog clusters.")
@click.option("--period", default="month", type=click.Choice(["month", "week"]), help="Trend period.")
def report(output_dir, max_features, n_clusters, period):
    """Run analysis and generate all reports."""
    from hn_intel.analyzer import compute_trends, detect_emerging_topics
    from hn_intel.network import extract_citations, build_citation_graph, compute_centrality
    from hn_intel.clusters import compute_blog_vectors, cluster_blogs, compute_similarity_matrix
    from hn_intel.reports import generate_all_reports

    conn = get_connection()
    init_db(conn)

    click.echo("Running analysis...")
    trends = compute_trends(conn, period=period)
    emerging = detect_emerging_topics(trends)

    extract_citations(conn)
    graph = build_citation_graph(conn)
    centrality = compute_centrality(graph)

    blog_vectors, blog_names, vectorizer = compute_blog_vectors(conn, max_features=max_features)
    clusters = cluster_blogs(blog_vectors, blog_names, vectorizer, n_clusters=n_clusters)
    sim_matrix = compute_similarity_matrix(blog_vectors)

    click.echo("Generating reports...")
    paths = generate_all_reports(
        trends=trends,
        emerging=emerging,
        centrality=centrality,
        graph=graph,
        cluster_results=clusters,
        similarity_matrix=sim_matrix,
        blog_names=blog_names,
        conn=conn,
        output_dir=output_dir,
    )

    conn.close()

    click.echo(f"\nReports written to {output_dir}/:")
    for path in paths:
        click.echo(f"  {path}")


if __name__ == "__main__":
    main()
