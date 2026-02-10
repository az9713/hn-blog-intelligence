"""Parse OPML files to extract RSS feed information."""

import xml.etree.ElementTree as ET


def parse_opml(path):
    """Parse an OPML file and return a list of feed dicts.

    Args:
        path: Path to the OPML file.

    Returns:
        List of dicts with keys: name, feed_url, site_url.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    feeds = []
    for outline in root.iter("outline"):
        if outline.get("type") == "rss":
            xml_url = outline.get("xmlUrl", "")
            if not xml_url:
                continue
            name = outline.get("text") or outline.get("title", "")
            feeds.append({
                "name": name,
                "feed_url": xml_url,
                "site_url": outline.get("htmlUrl", ""),
            })
    return feeds
