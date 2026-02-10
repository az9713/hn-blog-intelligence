"""Blog clustering using TF-IDF vectors and K-means."""

import html
import re
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from hn_intel.db import get_all_posts


def strip_html(text):
    """Remove HTML tags from text.

    Args:
        text: Raw HTML string, or None.

    Returns:
        Cleaned text with tags replaced by spaces.
    """
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return text.strip()


def compute_blog_vectors(conn, max_features=500):
    """Concatenate all posts per blog into one document and TF-IDF vectorize.

    Each blog becomes a single document composed of its posts' titles and
    stripped descriptions. The resulting TF-IDF matrix has one row per blog.

    Args:
        conn: sqlite3.Connection instance.
        max_features: Maximum number of TF-IDF features.

    Returns:
        Tuple of (tfidf_matrix, blog_names, vectorizer) where tfidf_matrix
        is a sparse matrix, blog_names is a list of blog name strings, and
        vectorizer is the fitted TfidfVectorizer.
    """
    posts = get_all_posts(conn)

    blog_docs = defaultdict(list)
    for post in posts:
        blog_name = post["blog_name"]
        title = post["title"] or ""
        description = strip_html(post["description"])
        blog_docs[blog_name].append(title + " " + description)

    blog_names = sorted(blog_docs.keys())
    documents = [" ".join(blog_docs[name]) for name in blog_names]

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b",
    )
    tfidf_matrix = vectorizer.fit_transform(documents)

    return tfidf_matrix, blog_names, vectorizer


def compute_similarity_matrix(blog_vectors):
    """Compute cosine similarity between all blog vectors.

    Args:
        blog_vectors: Sparse or dense TF-IDF matrix (one row per blog).

    Returns:
        Numpy 2D array of pairwise cosine similarities.
    """
    return cosine_similarity(blog_vectors)


def find_similar_blogs(similarity_matrix, blog_names, blog_name, top_n=5):
    """Find the most similar blogs to a given blog.

    Args:
        similarity_matrix: 2D numpy array of cosine similarities.
        blog_names: List of blog name strings matching matrix rows.
        blog_name: Name of the blog to find similarities for.
        top_n: Number of similar blogs to return.

    Returns:
        List of dicts with keys 'name' and 'similarity_score', sorted by
        descending similarity. Returns empty list if blog_name not found.
    """
    if blog_name not in blog_names:
        return []

    idx = blog_names.index(blog_name)
    similarities = similarity_matrix[idx]

    # Get indices sorted by similarity descending, excluding self
    ranked = np.argsort(similarities)[::-1]
    results = []
    for i in ranked:
        if i == idx:
            continue
        results.append({
            "name": blog_names[i],
            "similarity_score": float(similarities[i]),
        })
        if len(results) >= top_n:
            break

    return results


def cluster_blogs(blog_vectors, blog_names, vectorizer, n_clusters=8):
    """Cluster blogs using K-means on TF-IDF vectors.

    Each cluster is labelled by its top 5 centroid keywords.

    Args:
        blog_vectors: Sparse or dense TF-IDF matrix (one row per blog).
        blog_names: List of blog name strings matching matrix rows.
        vectorizer: Fitted TfidfVectorizer used to produce blog_vectors.
        n_clusters: Desired number of clusters (capped at number of blogs).

    Returns:
        List of cluster dicts, each with keys:
            cluster_id: Integer cluster identifier.
            label: Comma-separated string of top 5 keywords.
            blogs: List of blog name strings in this cluster.
    """
    k = min(n_clusters, len(blog_names))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(blog_vectors)

    feature_names = vectorizer.get_feature_names_out()
    clusters = []
    for cluster_id in range(k):
        centroid = km.cluster_centers_[cluster_id]
        top_indices = np.argsort(centroid)[::-1][:5]
        top_terms = [feature_names[i] for i in top_indices]
        label = ", ".join(top_terms)

        member_blogs = [
            blog_names[i] for i, lbl in enumerate(labels) if lbl == cluster_id
        ]

        clusters.append({
            "cluster_id": cluster_id,
            "label": label,
            "blogs": member_blogs,
        })

    return clusters
