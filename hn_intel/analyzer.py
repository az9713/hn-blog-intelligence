"""Trend analysis for HN blog posts using TF-IDF keyword extraction."""

import html
import re
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer

from hn_intel.db import get_all_posts


def strip_html(text):
    """Remove HTML tags from text.

    Args:
        text: Raw HTML string (or None).

    Returns:
        Plain text with tags removed.
    """
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return text.strip()


def extract_keywords(conn, max_features=500):
    """Run TF-IDF on title + stripped description for all posts.

    Args:
        conn: sqlite3.Connection instance.
        max_features: Maximum number of features for the vectorizer.

    Returns:
        Tuple of (fitted TfidfVectorizer, tfidf_matrix, list of post IDs).
        Returns (None, None, []) if there are no posts.
    """
    posts = get_all_posts(conn)
    if not posts:
        return None, None, []

    documents = []
    post_ids = []
    for post in posts:
        text = (post["title"] or "") + " " + strip_html(post["description"])
        documents.append(text)
        post_ids.append(post["id"])

    # Adjust min_df when corpus is too small
    min_df = min(3, len(documents))

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        min_df=min_df,
        max_df=0.7,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b",
    )
    tfidf_matrix = vectorizer.fit_transform(documents)
    return vectorizer, tfidf_matrix, post_ids


def _period_key(published, period):
    """Convert an ISO date string to a period bucket key.

    Args:
        published: ISO-format date string (e.g. '2024-01-15' or '2024-01-15T10:00:00').
        period: 'month' or 'week'.

    Returns:
        Period key string (e.g. '2024-01' for month, '2024-W03' for week).
        Returns None if the date cannot be parsed.
    """
    if not published:
        return None
    try:
        # Handle ISO format dates: take just the date part
        date_str = published[:10]
        parts = date_str.split("-")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

        if period == "week":
            from datetime import date

            d = date(year, month, day)
            iso_year, iso_week, _ = d.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        else:
            return f"{year}-{month:02d}"
    except (ValueError, IndexError):
        return None


def compute_trends(conn, period="month"):
    """Bucket posts by period, sum TF-IDF per keyword per period, normalize by post count.

    Args:
        conn: sqlite3.Connection instance.
        period: 'month' or 'week'.

    Returns:
        Dict of {period_key: {keyword: normalized_score}}.
        Empty dict if no posts or keywords found.
    """
    vectorizer, tfidf_matrix, post_ids = extract_keywords(conn)
    if vectorizer is None:
        return {}

    posts = get_all_posts(conn)
    id_to_post = {post["id"]: post for post in posts}
    feature_names = vectorizer.get_feature_names_out()

    # Group post indices by period
    period_indices = defaultdict(list)
    for idx, post_id in enumerate(post_ids):
        post = id_to_post.get(post_id)
        if post is None:
            continue
        key = _period_key(post["published"], period)
        if key:
            period_indices[key].append(idx)

    trends = {}
    for key, indices in sorted(period_indices.items()):
        post_count = len(indices)
        if post_count == 0:
            continue

        # Sum TF-IDF scores across posts in this period
        period_scores = {}
        for feat_idx, keyword in enumerate(feature_names):
            total = sum(tfidf_matrix[i, feat_idx] for i in indices)
            normalized = total / post_count
            if normalized > 0:
                period_scores[keyword] = float(normalized)

        if period_scores:
            trends[key] = period_scores

    return trends


def detect_emerging_topics(trends, window=3):
    """Compare recent period to historical average, flag acceleration > 2.0x.

    Args:
        trends: Dict from compute_trends: {period_key: {keyword: score}}.
        window: Number of recent periods to compare against history.

    Returns:
        List of dicts: {keyword, recent_score, historical_avg, acceleration},
        sorted by acceleration descending.
        Returns empty list if not enough data.
    """
    if not trends:
        return []

    sorted_periods = sorted(trends.keys())
    if len(sorted_periods) < window + 1:
        return []

    recent_periods = sorted_periods[-window:]
    historical_periods = sorted_periods[:-window]

    # Gather all keywords
    all_keywords = set()
    for scores in trends.values():
        all_keywords.update(scores.keys())

    emerging = []
    for keyword in all_keywords:
        recent_scores = [trends[p].get(keyword, 0.0) for p in recent_periods]
        recent_avg = sum(recent_scores) / len(recent_scores)

        historical_scores = [trends[p].get(keyword, 0.0) for p in historical_periods]
        historical_avg = sum(historical_scores) / len(historical_scores)

        if historical_avg > 0 and recent_avg > 0:
            acceleration = recent_avg / historical_avg
            if acceleration > 2.0:
                emerging.append(
                    {
                        "keyword": keyword,
                        "recent_score": round(recent_avg, 6),
                        "historical_avg": round(historical_avg, 6),
                        "acceleration": round(acceleration, 2),
                    }
                )

    emerging.sort(key=lambda x: x["acceleration"], reverse=True)
    return emerging


def find_leading_blogs(conn, keyword):
    """Find which blogs mentioned a keyword earliest and most frequently.

    Args:
        conn: sqlite3.Connection instance.
        keyword: Keyword string to search for in post titles and descriptions.

    Returns:
        List of dicts: {blog_name, first_mention, mention_count},
        sorted by first_mention ascending.
    """
    posts = get_all_posts(conn)
    keyword_lower = keyword.lower()

    blog_stats = defaultdict(lambda: {"count": 0, "first": None})

    for post in posts:
        text = ((post["title"] or "") + " " + strip_html(post["description"])).lower()
        if keyword_lower in text:
            blog_name = post["blog_name"]
            blog_stats[blog_name]["count"] += 1
            published = post["published"] or ""
            current_first = blog_stats[blog_name]["first"]
            if published and (current_first is None or published < current_first):
                blog_stats[blog_name]["first"] = published

    results = [
        {
            "blog_name": name,
            "first_mention": stats["first"] or "",
            "mention_count": stats["count"],
        }
        for name, stats in blog_stats.items()
    ]
    results.sort(key=lambda x: x["first_mention"] or "9999")
    return results
