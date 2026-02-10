"""Report generation for HN Blog Intelligence analysis results."""

import json
import os

import networkx as nx
from tabulate import tabulate


def generate_summary_report(trends, emerging, centrality, cluster_results, conn, output_dir):
    """Generate a summary Markdown report combining all analysis results.

    Args:
        trends: Dict from compute_trends: {period_key: {keyword: score}}.
        emerging: List of emerging topic dicts from detect_emerging_topics.
        centrality: Dict from compute_centrality: {blog_name: {pagerank, ...}}.
        cluster_results: List of cluster dicts from cluster_blogs.
        conn: sqlite3.Connection instance.
        output_dir: Directory to write the report file.

    Returns:
        Path to the generated summary.md file.
    """
    os.makedirs(output_dir, exist_ok=True)

    blog_count = conn.execute("SELECT COUNT(*) FROM blogs").fetchone()[0]
    post_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    min_date = conn.execute("SELECT MIN(published) FROM posts WHERE published != ''").fetchone()[0]
    max_date = conn.execute("SELECT MAX(published) FROM posts WHERE published != ''").fetchone()[0]

    lines = []
    lines.append("# HN Blog Intelligence Summary Report\n")

    # Dataset overview
    lines.append("## Dataset Overview\n")
    lines.append(f"- **Blogs**: {blog_count}")
    lines.append(f"- **Posts**: {post_count}")
    lines.append(f"- **Date range**: {min_date or 'N/A'} to {max_date or 'N/A'}")
    lines.append(f"- **Periods analyzed**: {len(trends)}")
    lines.append("")

    # Top emerging topics
    lines.append("## Top Emerging Topics\n")
    if emerging:
        top_emerging = emerging[:10]
        table_data = [
            [e["keyword"], f"{e['acceleration']:.2f}x", f"{e['recent_score']:.6f}"]
            for e in top_emerging
        ]
        lines.append(tabulate(
            table_data,
            headers=["Keyword", "Acceleration", "Recent Score"],
            tablefmt="github",
        ))
    else:
        lines.append("No emerging topics detected.")
    lines.append("")

    # Most-cited blogs by PageRank
    lines.append("## Most-Cited Blogs (by PageRank)\n")
    if centrality:
        sorted_blogs = sorted(
            centrality.items(), key=lambda x: x[1]["pagerank"], reverse=True
        )[:10]
        table_data = [
            [name, f"{metrics['pagerank']:.6f}", metrics["in_degree"], metrics["out_degree"]]
            for name, metrics in sorted_blogs
        ]
        lines.append(tabulate(
            table_data,
            headers=["Blog", "PageRank", "In-Degree", "Out-Degree"],
            tablefmt="github",
        ))
    else:
        lines.append("No citation data available.")
    lines.append("")

    # Cluster summary
    lines.append("## Blog Clusters\n")
    if cluster_results:
        table_data = [
            [c["cluster_id"], c["label"], len(c["blogs"]), ", ".join(c["blogs"][:3])]
            for c in cluster_results
        ]
        lines.append(tabulate(
            table_data,
            headers=["Cluster", "Label", "Blog Count", "Sample Blogs"],
            tablefmt="github",
        ))
    else:
        lines.append("No cluster data available.")
    lines.append("")

    path = os.path.join(output_dir, "summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path


def generate_trend_report(trends, emerging, output_dir):
    """Generate trend analysis report in Markdown and JSON.

    Args:
        trends: Dict from compute_trends: {period_key: {keyword: score}}.
        emerging: List of emerging topic dicts from detect_emerging_topics.
        output_dir: Directory to write report files.

    Returns:
        Tuple of (md_path, json_path) for the generated files.
    """
    os.makedirs(output_dir, exist_ok=True)

    lines = []
    lines.append("# Trend Analysis Report\n")

    lines.append("## Emerging Topics\n")
    if emerging:
        table_data = [
            [e["keyword"], f"{e['acceleration']:.2f}x", f"{e['recent_score']:.6f}", f"{e['historical_avg']:.6f}"]
            for e in emerging
        ]
        lines.append(tabulate(
            table_data,
            headers=["Keyword", "Acceleration", "Recent Score", "Historical Avg"],
            tablefmt="github",
        ))
    else:
        lines.append("No emerging topics detected.")
    lines.append("")

    lines.append("## Period Summary\n")
    lines.append(f"Total periods: {len(trends)}\n")
    if trends:
        sorted_periods = sorted(trends.keys())
        lines.append(f"- First period: {sorted_periods[0]}")
        lines.append(f"- Last period: {sorted_periods[-1]}")
    lines.append("")

    md_path = os.path.join(output_dir, "trends.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    json_data = {
        "periods": {k: v for k, v in sorted(trends.items())},
        "emerging_topics": emerging,
    }
    json_path = os.path.join(output_dir, "trends.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    return md_path, json_path


def generate_network_report(centrality, graph, output_dir):
    """Generate network analysis report in Markdown and JSON.

    Args:
        centrality: Dict from compute_centrality: {blog_name: {pagerank, ...}}.
        graph: networkx.DiGraph from build_citation_graph.
        output_dir: Directory to write report files.

    Returns:
        Tuple of (md_path, json_path) for the generated files.
    """
    os.makedirs(output_dir, exist_ok=True)

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    density = nx.density(graph) if node_count > 0 else 0.0

    lines = []
    lines.append("# Network Analysis Report\n")

    lines.append("## Graph Statistics\n")
    lines.append(f"- **Nodes (blogs)**: {node_count}")
    lines.append(f"- **Edges (citations)**: {edge_count}")
    lines.append(f"- **Density**: {density:.6f}")
    lines.append("")

    lines.append("## Top Blogs by PageRank\n")
    if centrality:
        sorted_by_pr = sorted(
            centrality.items(), key=lambda x: x[1]["pagerank"], reverse=True
        )[:20]
        table_data = [
            [name, f"{m['pagerank']:.6f}", m["in_degree"], m["out_degree"]]
            for name, m in sorted_by_pr
        ]
        lines.append(tabulate(
            table_data,
            headers=["Blog", "PageRank", "In-Degree", "Out-Degree"],
            tablefmt="github",
        ))
    else:
        lines.append("No centrality data available.")
    lines.append("")

    lines.append("## Top Blogs by Betweenness Centrality\n")
    if centrality:
        sorted_by_btwn = sorted(
            centrality.items(), key=lambda x: x[1]["betweenness"], reverse=True
        )[:20]
        table_data = [
            [name, f"{m['betweenness']:.6f}"]
            for name, m in sorted_by_btwn
        ]
        lines.append(tabulate(
            table_data,
            headers=["Blog", "Betweenness"],
            tablefmt="github",
        ))
    else:
        lines.append("No centrality data available.")
    lines.append("")

    md_path = os.path.join(output_dir, "network.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    json_data = {
        "graph_stats": {
            "nodes": node_count,
            "edges": edge_count,
            "density": density,
        },
        "centrality": centrality,
    }
    json_path = os.path.join(output_dir, "network.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    return md_path, json_path


def generate_cluster_report(cluster_results, similarity_matrix, blog_names, output_dir):
    """Generate cluster analysis report in Markdown and JSON.

    Args:
        cluster_results: List of cluster dicts from cluster_blogs.
        similarity_matrix: 2D numpy array of cosine similarities.
        blog_names: List of blog name strings matching matrix rows.
        output_dir: Directory to write report files.

    Returns:
        Tuple of (md_path, json_path) for the generated files.
    """
    os.makedirs(output_dir, exist_ok=True)

    lines = []
    lines.append("# Blog Cluster Report\n")

    lines.append("## Cluster Assignments\n")
    if cluster_results:
        for cluster in cluster_results:
            lines.append(f"### Cluster {cluster['cluster_id']}: {cluster['label']}\n")
            for blog in cluster["blogs"]:
                lines.append(f"- {blog}")
            lines.append("")
    else:
        lines.append("No cluster data available.")
        lines.append("")

    lines.append("## Similar Blog Pairs\n")
    if similarity_matrix is not None and len(blog_names) > 0:
        from hn_intel.clusters import find_similar_blogs

        table_data = []
        for name in blog_names:
            similar = find_similar_blogs(similarity_matrix, blog_names, name, top_n=5)
            for s in similar:
                table_data.append([name, s["name"], f"{s['similarity_score']:.4f}"])

        if table_data:
            lines.append(tabulate(
                table_data,
                headers=["Blog", "Similar To", "Score"],
                tablefmt="github",
            ))
        else:
            lines.append("No similarity data available.")
    else:
        lines.append("No similarity data available.")
    lines.append("")

    md_path = os.path.join(output_dir, "clusters.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    json_data = {
        "clusters": cluster_results,
        "blog_similarities": {},
    }
    if similarity_matrix is not None and len(blog_names) > 0:
        from hn_intel.clusters import find_similar_blogs

        for name in blog_names:
            similar = find_similar_blogs(similarity_matrix, blog_names, name, top_n=5)
            json_data["blog_similarities"][name] = similar

    json_path = os.path.join(output_dir, "clusters.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    return md_path, json_path


def generate_all_reports(trends, emerging, centrality, graph, cluster_results,
                         similarity_matrix, blog_names, conn, output_dir):
    """Generate all reports at once.

    Args:
        trends: Dict from compute_trends.
        emerging: List from detect_emerging_topics.
        centrality: Dict from compute_centrality.
        graph: networkx.DiGraph from build_citation_graph.
        cluster_results: List from cluster_blogs.
        similarity_matrix: 2D numpy array from compute_similarity_matrix.
        blog_names: List of blog name strings.
        conn: sqlite3.Connection instance.
        output_dir: Directory to write report files.

    Returns:
        List of file paths created.
    """
    paths = []

    summary_path = generate_summary_report(
        trends, emerging, centrality, cluster_results, conn, output_dir
    )
    paths.append(summary_path)

    trend_md, trend_json = generate_trend_report(trends, emerging, output_dir)
    paths.extend([trend_md, trend_json])

    network_md, network_json = generate_network_report(centrality, graph, output_dir)
    paths.extend([network_md, network_json])

    cluster_md, cluster_json = generate_cluster_report(
        cluster_results, similarity_matrix, blog_names, output_dir
    )
    paths.extend([cluster_md, cluster_json])

    return paths
