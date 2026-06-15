import os
import sys
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime

# Add parent plugins directory so we can import the shared DB module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chief_of_staff_db

OPPORTUNITY_KEYWORDS = [
    "scholarship", "fellowship", "summer school", "summer camp",
    "free course", "coupon", "grant", "fintech", "internship",
    "backend django", "python developer", "backend engineer", "ocr", "remote dev"
]


def _parse_rss_feed(feed_url: str) -> list:
    """Parses a standard RSS feed using standard library xml parser."""
    items = []
    try:
        req = urllib.request.Request(
            feed_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        for item in root.findall('.//item'):
            title = item.find('title')
            link = item.find('link')
            description = item.find('description')

            title_text = title.text.strip() if title is not None and title.text else "No Title"
            link_text = link.text.strip() if link is not None and link.text else ""
            desc_text = description.text.strip() if description is not None and description.text else ""

            items.append({
                "title": title_text,
                "url": link_text,
                "description": desc_text[:300]
            })
    except Exception as e:
        print(f"Error parsing RSS feed {feed_url}: {e}")
    return items


def _parse_hn_search(query: str) -> list:
    """Queries Hacker News Algolia Search API for recent targeted stories."""
    items = []
    url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(query)}&tags=story"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        for hit in data.get("hits", []):
            title = hit.get("title", "")
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            desc = f"HN Points: {hit.get('points', 0)} | Comments: {hit.get('num_comments', 0)}"

            items.append({
                "title": title,
                "url": story_url,
                "description": desc
            })
    except Exception as e:
        print(f"Error querying HN API: {e}")
    return items


def _trigger_crawlers() -> str:
    """
    Runs background crawlers to scrape remote backend jobs and global academic/professional opportunities,
    filtering and storing relevant items in SQLite.
    """
    total_scraped = 0
    new_found = 0
    scraped_items = []

    scraped_items.extend(
        _parse_rss_feed("https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss")
    )
    scraped_items.extend(_parse_hn_search("scholarship"))
    scraped_items.extend(_parse_hn_search("fellowship"))
    scraped_items.extend(_parse_hn_search("summer school"))

    for item in scraped_items:
        title_lower = item["title"].lower()
        desc_lower = item["description"].lower()

        matches_profile = any(kw in title_lower or kw in desc_lower for kw in OPPORTUNITY_KEYWORDS)
        if not matches_profile:
            continue

        total_scraped += 1

        opp_type = "other"
        if any(w in title_lower for w in ["job", "engineer", "developer", "backend", "programmer"]):
            opp_type = "job"
        elif any(w in title_lower for w in ["scholarship", "fellowship", "phd", "academic"]):
            opp_type = "scholarship"
        elif any(w in title_lower for w in ["camp", "school", "residency", "summer"]):
            opp_type = "course"
        elif any(w in title_lower for w in ["coupon", "free", "discount"]):
            opp_type = "coupon"

        is_new = chief_of_staff_db.add_opportunity(
            title=item["title"],
            url=item["url"],
            opp_type=opp_type,
            description=item["description"]
        )
        if is_new:
            new_found += 1

    chief_of_staff_db.log_telemetry(
        event_type="crawler_executed",
        details={
            "total_evaluated": len(scraped_items),
            "matched_keywords": total_scraped,
            "new_stored": new_found,
            "executed_at": datetime.now().isoformat()
        }
    )

    return (
        f"🤖 **Opportunity Crawler Completed**!\n"
        f"- Scraped Feeds: WeWorkRemotely, Hacker News API\n"
        f"- Matched Profile Keywords: {total_scraped}\n"
        f"- New Opportunities Stored: {new_found} (Cached in SQLite)"
    )


def _pull_cached_opportunities(limit: int = 5) -> str:
    """
    Retrieves a bulleted summary of unread opportunities from the SQLite database
    and marks them as 'sent' so you don't receive them twice.
    """
    unread = chief_of_staff_db.get_unread_opportunities(limit=limit)
    if not unread:
        return "✨ **Global Opportunity Radar**: No new unread opportunities matching your profile today."

    output = ["🌐 **Global Opportunity Arbitrage Radar**:\n"]
    for idx, opp in enumerate(unread, 1):
        chief_of_staff_db.update_opportunity_status(opp["id"], "sent")

        classification = opp["type"].upper()
        output.append(
            f"{idx}. **[{classification}]** {opp['title']}\n"
            f"   - *Link*: {opp['url']}\n"
            f"   - *Detail*: {opp['description'][:150]}..."
        )

    return "\n".join(output)


def register(ctx):
    """Hermes plugin registration entrypoint."""
    ctx.register_tool(
        name="run_opportunity_crawler",
        toolset="opportunity-radar",
        schema={
            "type": "object",
            "properties": {}
        },
        handler=lambda args, **kwargs: _trigger_crawlers()
    )
    ctx.register_tool(
        name="pull_radar_opportunities",
        toolset="opportunity-radar",
        schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of opportunities to return (default 5)."
                }
            }
        },
        handler=lambda args, **kwargs: _pull_cached_opportunities(args.get("limit", 5))
    )
