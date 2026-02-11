"""Surface high-impact project ideas from HN blog pain signals."""

import html
import math
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from hn_intel.db import get_all_posts

# ── Pain-trigger stop words (excluded from TF-IDF to keep labels meaningful) ─

_PAIN_STOP_WORDS = [
    "wish", "would", "nice", "someone", "should", "hope", "really", "need",
    "frustrat", "frustrating", "frustrated", "frustration", "annoy", "annoying", "annoyed",
    "pain", "point", "drives", "crazy", "maddening",
    "good", "way", "tool", "solution", "missing", "lacking", "gap",
    "underserved", "easy", "reliable", "decent", "still", "exist", "unmet",
    "hard", "difficult", "impossible", "struggle", "struggling", "complicated",
    "complex", "long", "painful",
    "broken", "work", "unreliable", "flaky", "buggy", "unusable", "failing", "fragile",
    "opportunity", "untapped", "demand", "ripe", "disruption", "market", "room", "space", "begging",
    "people", "things", "just", "like", "think", "know", "want", "make", "going",
    "don", "doesn", "didn", "isn", "wasn", "aren", "won", "can",
    "lot", "much", "many", "even", "also", "actually", "right", "new", "old",
    "try", "tried", "trying", "able", "said", "says", "kind", "sort",
    "got", "gets", "makes", "making", "getting", "having",
    "experience", "thoughts", "state", "future", "woes",
    "problems", "issues", "troubles", "challenges",
    "does", "did", "doing", "done", "goes", "went", "going",
    "take", "took", "taking", "taken", "give", "gave", "given",
    "find", "finding", "found", "read", "reading", "write", "writing",
    "come", "came", "coming", "look", "looking", "looked",
    "see", "seeing", "seen", "tell", "telling", "told",
    "become", "became", "means", "put", "bring", "brought",
    "change", "changes", "changing", "update", "updates",
    "inside", "outside", "around", "across", "between",
    "pretty", "quite", "rather", "enough", "almost",
    "certain", "probably", "maybe", "perhaps", "likely",
    "seem", "seems", "appear", "appears", "happened",
    "ways", "wrong", "important", "impact", "formation",
    "piece", "thing", "things", "bad", "single", "feel", "feels",
    "real", "best", "least", "full", "fact", "based",
    "top", "high", "low", "big", "small", "whole",
    "point", "case", "type", "step", "form",
    "use", "used", "uses", "month", "months", "years",
    "number", "example", "question", "answer", "idea",
    "post", "blog", "article", "page", "site", "link",
]

# ── Label templates by dominant pain type ────────────────────────────────────

_LABEL_TEMPLATES = {
    "wish":        "Better {}",
    "frustration": "Improved {}",
    "gap":         "{} Solution",
    "difficulty":  "Simplified {}",
    "broken":      "Reliable {}",
    "opportunity": "{} Platform",
}

# ── Pain-signal patterns ────────────────────────────────────────────────────

_PAIN_PATTERNS = {
    "wish": re.compile(
        r"(?:i wish|would be nice|if only|someone should build|wish there was|"
        r"wish someone would|hope someone builds|we really need)",
        re.IGNORECASE,
    ),
    "frustration": re.compile(
        r"(?:frustrat\w*|annoy\w*|pain point|drives me crazy|infuriat\w*|"
        r"maddening|exasperat\w*|fed up with)",
        re.IGNORECASE,
    ),
    "gap": re.compile(
        r"(?:no good (?:way|tool|solution)|missing|lacking|gap in|underserved|"
        r"no (?:easy|reliable|decent) way|still no|doesn't exist|"
        r"yet to see a good|unmet need)",
        re.IGNORECASE,
    ),
    "difficulty": re.compile(
        r"(?:hard to|difficult to|impossible to|struggle with|struggling to|"
        r"too complicated|overly complex|shouldn't be this hard|"
        r"takes too long to|painful to)",
        re.IGNORECASE,
    ),
    "broken": re.compile(
        r"(?:broken|doesn't work|unreliable|flaky|buggy|unusable|"
        r"constantly break\w*|keeps failing|fragile)",
        re.IGNORECASE,
    ),
    "opportunity": re.compile(
        r"(?:opportunity|untapped|need for|demand for|ripe for disruption|"
        r"market for|room for|space for a|begging for)",
        re.IGNORECASE,
    ),
}

# Sentence boundary pattern
_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?\n]?")


def _strip_html(text):
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return text.strip()


def _extract_sentence(text, match_start, match_end):
    """Extract the sentence surrounding a regex match.

    Args:
        text: Full plain-text string.
        match_start: Start index of the regex match.
        match_end: End index of the regex match.

    Returns:
        The sentence containing the match, trimmed.
    """
    for m in _SENTENCE_RE.finditer(text):
        if m.start() <= match_start and m.end() >= match_end:
            return m.group().strip()
    # Fallback: return a window around the match
    start = max(0, match_start - 80)
    end = min(len(text), match_end + 80)
    return text[start:end].strip()


def _extract_context(text, match_start, match_end, max_sentences=3):
    """Extract 2-3 sentences surrounding a regex match for richer context."""
    sentences = list(_SENTENCE_RE.finditer(text))
    for i, m in enumerate(sentences):
        if m.start() <= match_start and m.end() >= match_end:
            start_idx = max(0, i - 1)
            end_idx = min(len(sentences), i + max_sentences - 1)
            parts = [sentences[j].group().strip() for j in range(start_idx, end_idx)]
            return " ".join(parts)
    # Fallback: wider window
    start = max(0, match_start - 150)
    end = min(len(text), match_end + 150)
    return text[start:end].strip()


def _compute_location_hint(match_start, title_len, text_len):
    """Return a location hint like 'in the title' or 'near the beginning'."""
    if match_start < title_len:
        return "in the title"
    # Position within the description body (after title)
    body_pos = (match_start - title_len) / max(text_len - title_len, 1)
    if body_pos < 0.33:
        return "near the beginning"
    elif body_pos < 0.66:
        return "midway through"
    else:
        return "near the end"


# ── Public API ──────────────────────────────────────────────────────────────


def extract_pain_signals(conn, max_age_days=365):
    """Scan all posts for pain-point language and return structured signals.

    Each signal includes full back-pointer data to the source blog and post.

    Args:
        conn: sqlite3.Connection instance.
        max_age_days: Skip posts older than this many days. Posts with
            missing or unparseable dates are kept (conservative).

    Returns:
        List of dicts, each with keys: post_id, blog_id, blog_name,
        post_title, post_url, published, signal_text, signal_type,
        signal_context, signal_location.
    """
    posts = get_all_posts(conn)
    signals = []
    # Track (post_url, signal_type) → longest signal_text to deduplicate
    seen = {}

    today = date.today()
    cutoff = today - timedelta(days=max_age_days)

    for post in posts:
        # Skip posts older than cutoff
        pub = post["published"] or ""
        if pub:
            try:
                pub_date = date.fromisoformat(pub[:10])
                if pub_date < cutoff:
                    continue
            except (ValueError, IndexError):
                pass  # keep posts with unparseable dates
        title = post["title"] or ""
        description = _strip_html(post["description"])
        full_text = title + ". " + description
        title_len = len(title) + 2  # account for ". " separator

        for signal_type, pattern in _PAIN_PATTERNS.items():
            for match in pattern.finditer(full_text):
                sentence = _extract_sentence(full_text, match.start(), match.end())
                if len(sentence) < 10:
                    continue

                key = (post["url"], signal_type)
                if key in seen:
                    # Keep the longest match per post+type
                    if len(sentence) > len(seen[key]["signal_text"]):
                        seen[key]["signal_text"] = sentence
                        seen[key]["signal_context"] = _extract_context(
                            full_text, match.start(), match.end()
                        )
                        seen[key]["signal_location"] = _compute_location_hint(
                            match.start(), title_len, len(full_text)
                        )
                    continue

                signal = {
                    "post_id": post["id"],
                    "blog_id": post["blog_id"],
                    "blog_name": post["blog_name"],
                    "post_title": title,
                    "post_url": post["url"],
                    "published": post["published"] or "",
                    "signal_text": sentence,
                    "signal_type": signal_type,
                    "signal_context": _extract_context(
                        full_text, match.start(), match.end()
                    ),
                    "signal_location": _compute_location_hint(
                        match.start(), title_len, len(full_text)
                    ),
                }
                seen[key] = signal
                signals.append(signal)

    return signals


def extract_signal_keywords(signals, max_features=200):
    """Run TF-IDF on signal texts to identify topics for clustering.

    Args:
        signals: List of signal dicts from extract_pain_signals.
        max_features: Maximum TF-IDF features.

    Returns:
        Tuple of (fitted TfidfVectorizer, tfidf_matrix).
        Returns (None, None) if fewer than 2 signals.
    """
    if len(signals) < 2:
        return None, None

    # Combine post title (weighted 2x) with signal text so clustering
    # groups by topic rather than just pain expression similarity
    documents = [
        "{t} {t} {s}".format(t=s.get("post_title", ""), s=s["signal_text"])
        for s in signals
    ]
    min_df = min(2, len(documents))

    # Combine sklearn's English stop words with pain-trigger vocabulary
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    combined_stop_words = list(ENGLISH_STOP_WORDS) + _PAIN_STOP_WORDS

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words=combined_stop_words,
        min_df=min_df,
        max_df=0.8,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{2,}\b",
    )
    matrix = vectorizer.fit_transform(documents)
    return vectorizer, matrix


def score_ideas(signals, emerging, centrality):
    """Compute a composite impact score for each pain signal.

    Scoring dimensions:
        - trend (0.35): keyword overlap with emerging topics
        - authority (0.25): PageRank of the source blog
        - breadth (0.25): fraction of distinct blogs with similar pain
        - recency (0.15): exponential decay from today

    Args:
        signals: List of signal dicts.
        emerging: List of emerging topic dicts from detect_emerging_topics.
        centrality: Dict from compute_centrality: {blog_name: {pagerank, ...}}.

    Returns:
        The same signals list, with 'impact_score' and 'score_breakdown' added.
    """
    if not signals:
        return signals

    # Build lookup structures
    emerging_keywords = {}
    for e in (emerging or []):
        emerging_keywords[e["keyword"]] = e["acceleration"]
    max_accel = max(emerging_keywords.values()) if emerging_keywords else 1.0

    max_pr = 0.0
    if centrality:
        max_pr = max(m["pagerank"] for m in centrality.values()) or 1.0

    total_blogs = len({s["blog_name"] for s in signals}) or 1

    # Determine the most recent date for recency decay
    today = date.today()

    for sig in signals:
        # ── Trend momentum ──
        trend_score = 0.0
        sig_words = set(sig["signal_text"].lower().split())
        for kw, accel in emerging_keywords.items():
            kw_parts = set(kw.lower().split())
            if kw_parts & sig_words:
                trend_score = max(trend_score, accel / max_accel)
        trend_score = min(trend_score, 1.0)

        # ── Authority ──
        auth_score = 0.0
        if centrality and sig["blog_name"] in centrality:
            auth_score = centrality[sig["blog_name"]]["pagerank"] / max_pr
        auth_score = min(auth_score, 1.0)

        # ── Breadth ──
        breadth_score = 0.0  # will be filled during clustering

        # ── Recency ──
        recency_score = 0.0
        pub = sig.get("published", "")
        if pub:
            try:
                pub_date = date.fromisoformat(pub[:10])
                days_ago = (today - pub_date).days
                recency_score = math.exp(-days_ago / 365.0)
            except (ValueError, IndexError):
                pass
        recency_score = min(recency_score, 1.0)

        sig["score_breakdown"] = {
            "trend": round(trend_score, 4),
            "authority": round(auth_score, 4),
            "breadth": round(breadth_score, 4),
            "recency": round(recency_score, 4),
        }
        sig["impact_score"] = round(
            0.35 * trend_score
            + 0.25 * auth_score
            + 0.25 * breadth_score
            + 0.15 * recency_score,
            4,
        )

    return signals


def build_justification(idea):
    """Generate a written justification for a project idea.

    Explains *why* this is a high-impact idea using evidence from the
    signals, trend data, and authority data.

    Args:
        idea: A single idea dict produced by cluster_signals.

    Returns:
        Multi-sentence justification string.
    """
    parts = []

    blog_count = idea["blog_count"]
    signal_count = idea["signal_count"]
    blog_names = [s["blog_name"] for s in idea["sources"][:5]]
    unique_names = list(dict.fromkeys(blog_names))  # dedupe, preserve order

    # Evidence breadth
    if blog_count >= 3:
        names_str = ", ".join(unique_names[:3])
        parts.append(
            f"{blog_count} blogs independently describe this need, "
            f"including {names_str}."
        )
    elif blog_count > 0:
        names_str = " and ".join(unique_names)
        parts.append(
            f"Raised by {names_str} ({signal_count} "
            f"signal{'s' if signal_count != 1 else ''})."
        )

    # Pain type breakdown
    breakdown = idea.get("pain_type_breakdown", {})
    if breakdown:
        bd_parts = [f"{count} {ptype}" for ptype, count in
                     sorted(breakdown.items(), key=lambda x: -x[1])]
        parts.append(
            f"Pain signals span {', '.join(bd_parts)} "
            f"{'categories' if len(bd_parts) > 1 else 'category'}."
        )

    # Keywords / trend connection
    keywords = idea.get("keywords", [])
    if keywords:
        parts.append(
            f"Related trending topics: {', '.join(keywords[:5])}."
        )

    # Impact score summary
    score = idea.get("impact_score", 0)
    if score >= 0.7:
        parts.append("High impact score suggests strong demand for a solution.")
    elif score >= 0.4:
        parts.append("Moderate impact score indicates a viable project opportunity.")

    return " ".join(parts) if parts else "Potential opportunity identified from blog content."


def cluster_signals(signals, vectorizer, matrix, similarity_threshold=0.5):
    """Group related pain signals into coherent project idea themes.

    Uses agglomerative clustering on TF-IDF vectors of signal texts.

    Args:
        signals: List of scored signal dicts.
        vectorizer: Fitted TfidfVectorizer from extract_signal_keywords.
        matrix: TF-IDF matrix from extract_signal_keywords.
        similarity_threshold: Distance threshold for clustering.

    Returns:
        List of idea dicts, each with: idea_id, label, impact_score,
        justification, keywords, signal_count, blog_count,
        pain_type_breakdown, representative_quote, sources.
    """
    if not signals:
        return []

    # Single signal → single idea
    if len(signals) == 1 or vectorizer is None or matrix is None:
        sig = signals[0]
        idea = _make_idea(0, signals, [], [])
        return [idea]

    # Agglomerative clustering with cosine distance
    sim = cosine_similarity(matrix)
    distance = 1.0 - sim
    # Clip small negative values from floating-point imprecision
    distance[distance < 0] = 0

    n_samples = matrix.shape[0]
    # distance_threshold in agglomerative uses the distance metric
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1.0 - similarity_threshold,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(distance)

    feature_names = list(vectorizer.get_feature_names_out())

    # Group signals by cluster label
    cluster_groups = defaultdict(list)
    cluster_indices = defaultdict(list)
    for idx, label in enumerate(labels):
        cluster_groups[label].append(signals[idx])
        cluster_indices[label].append(idx)

    ideas = []
    for idea_id, (label, members) in enumerate(
        sorted(cluster_groups.items(), key=lambda x: x[0])
    ):
        indices = cluster_indices[label]
        idea = _make_idea(idea_id, members, feature_names, indices, matrix)
        ideas.append(idea)

    # Update breadth scores and re-rank
    total_blogs = len({s["blog_name"] for s in signals}) or 1
    for idea in ideas:
        breadth = idea["blog_count"] / total_blogs
        for src in idea["sources"]:
            src["score_breakdown"]["breadth"] = round(breadth, 4)
            src["impact_score"] = round(
                0.35 * src["score_breakdown"]["trend"]
                + 0.25 * src["score_breakdown"]["authority"]
                + 0.25 * breadth
                + 0.15 * src["score_breakdown"]["recency"],
                4,
            )
        idea["impact_score"] = round(
            max(s["impact_score"] for s in idea["sources"]), 4
        )
        idea["justification"] = build_justification(idea)

    ideas.sort(key=lambda x: x["impact_score"], reverse=True)
    # Re-number after sorting
    for i, idea in enumerate(ideas):
        idea["idea_id"] = i

    return ideas


def _generate_label(keywords, pain_type_breakdown):
    """Generate a human-readable label from keywords and dominant pain type.

    Args:
        keywords: List of top TF-IDF keywords for this cluster.
        pain_type_breakdown: Dict of {pain_type: count}.

    Returns:
        A template-based label like "Simplified Database Migration".
    """
    if not keywords:
        return "General Improvement"

    # Pick the dominant pain type
    dominant = max(pain_type_breakdown, key=pain_type_breakdown.get) if pain_type_breakdown else "wish"
    template = _LABEL_TEMPLATES.get(dominant, "Better {}")

    # Use up to 3 keywords, title-cased
    topic = " ".join(kw.title() for kw in keywords[:3])
    return template.format(topic)


def _extract_title_keywords(members, max_keywords=5, vocabulary=None):
    """Extract meaningful keywords from post titles in a cluster.

    Strategy:
    1. Find words appearing in 2+ titles (cluster theme words).
    2. If not enough, supplement from highest-impact member's title.
    3. If a TF-IDF vocabulary is provided, prefer words that appear in the
       broader corpus (filters out rare proper nouns and noise).

    Args:
        members: List of signal dicts from a cluster.
        max_keywords: Maximum number of keywords to return.
        vocabulary: Optional set of corpus-wide TF-IDF feature names.
            Words in the vocabulary are preferred for relevance.

    Returns:
        List of keyword strings representing the cluster topic.
    """
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    combined_stop = set(ENGLISH_STOP_WORDS) | set(_PAIN_STOP_WORDS)

    token_re = re.compile(r"\b[a-zA-Z][a-zA-Z0-9]{2,}\b")

    # Collect document frequency across all titles
    word_freq = defaultdict(int)
    for m in members:
        title = m.get("post_title", "")
        tokens = token_re.findall(title.lower())
        for t in set(tokens):
            if t not in combined_stop:
                word_freq[t] += 1

    # Filter: prefer words in the corpus vocabulary (removes rare noise)
    if vocabulary:
        filtered = {w: c for w, c in word_freq.items() if w in vocabulary}
        if filtered:
            word_freq = filtered

    # Start with words appearing in 2+ titles (cluster theme)
    common = sorted(
        [(w, c) for w, c in word_freq.items() if c >= 2],
        key=lambda x: (-x[1], x[0]),
    )
    keywords = [w for w, c in common]

    if len(keywords) >= max_keywords:
        return keywords[:max_keywords]

    # Supplement with keywords from the highest-impact member's title
    sorted_members = sorted(
        members, key=lambda m: m.get("impact_score", 0), reverse=True
    )
    used = set(keywords)
    vocab_set = vocabulary or set()
    for m in sorted_members:
        title = m.get("post_title", "")
        tokens = token_re.findall(title.lower())
        for t in tokens:
            if t not in combined_stop and t not in used:
                # When vocabulary available, only use corpus-attested words
                if vocab_set and t not in vocab_set:
                    continue
                keywords.append(t)
                used.add(t)
                if len(keywords) >= max_keywords:
                    return keywords[:max_keywords]

    return keywords[:max_keywords]


def _make_idea(idea_id, members, feature_names, indices, matrix=None):
    """Build a single idea dict from a cluster of signals."""
    # Extract keywords from post titles (more topical than signal text)
    # Pass TF-IDF vocabulary as relevance filter for title words
    vocab = set(feature_names) if feature_names else None
    keywords = _extract_title_keywords(members, vocabulary=vocab)

    blog_names_seen = set()
    for m in members:
        blog_names_seen.add(m["blog_name"])

    # Pain type breakdown
    pain_types = defaultdict(int)
    for m in members:
        pain_types[m["signal_type"]] += 1

    # Representative quote = highest-scored signal
    sorted_members = sorted(members, key=lambda x: x.get("impact_score", 0), reverse=True)
    rep_quote = sorted_members[0]["signal_text"] if sorted_members else ""

    sources = [
        {
            "blog_name": m["blog_name"],
            "post_title": m["post_title"],
            "post_url": m["post_url"],
            "published": m["published"],
            "signal_text": m["signal_text"],
            "signal_type": m["signal_type"],
            "signal_context": m.get("signal_context", ""),
            "signal_location": m.get("signal_location", ""),
            "impact_score": m.get("impact_score", 0),
            "score_breakdown": m.get("score_breakdown", {}),
        }
        for m in sorted_members
    ]

    label = _generate_label(keywords, dict(pain_types))
    agg_score = max((m.get("impact_score", 0) for m in members), default=0)

    return {
        "idea_id": idea_id,
        "label": label,
        "impact_score": round(agg_score, 4),
        "justification": "",  # filled after breadth update
        "keywords": keywords,
        "signal_count": len(members),
        "blog_count": len(blog_names_seen),
        "pain_type_breakdown": dict(pain_types),
        "representative_quote": rep_quote,
        "sources": sources,
    }


def generate_ideas(conn, max_features=500, period="month", top_n=20, max_age_days=365):
    """Orchestrate the full ideas pipeline.

    1. Extract pain signals from posts
    2. Fetch emerging trends and blog centrality from existing modules
    3. Score, cluster, and rank signals into project ideas

    Args:
        conn: sqlite3.Connection instance.
        max_features: Max TF-IDF features for trend analysis.
        period: 'month' or 'week' for trend bucketing.
        top_n: Maximum number of ideas to return.
        max_age_days: Skip posts older than this many days.

    Returns:
        List of idea dicts sorted by impact_score descending.
    """
    from hn_intel.analyzer import compute_trends, detect_emerging_topics
    from hn_intel.network import extract_citations, build_citation_graph, compute_centrality

    # Step 1: extract pain signals
    signals = extract_pain_signals(conn, max_age_days=max_age_days)
    if not signals:
        return []

    # Step 2: get trend and authority data
    trends = compute_trends(conn, period=period)
    emerging = detect_emerging_topics(trends)

    extract_citations(conn)
    graph = build_citation_graph(conn)
    centrality = compute_centrality(graph)

    # Step 3: vectorize signals
    vectorizer, matrix = extract_signal_keywords(signals, max_features=min(200, max_features))

    # Step 4: score
    signals = score_ideas(signals, emerging, centrality)

    # Step 5: cluster into ideas
    ideas = cluster_signals(signals, vectorizer, matrix)

    # Filter out low-quality singleton ideas (single blog, single signal)
    quality_ideas = [i for i in ideas if i["blog_count"] >= 2]
    if quality_ideas:
        ideas = quality_ideas

    # Re-number after filtering to avoid gaps
    for i, idea in enumerate(ideas):
        idea["idea_id"] = i

    return ideas[:top_n]
