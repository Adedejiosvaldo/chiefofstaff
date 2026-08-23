import os
import sys
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from . import db

DEVOPS_KEYWORDS = [
    "devops", "sre", "site reliability", "platform engineer", "cloud engineer",
    "infrastructure", "kubernetes", "k8s", "terraform", "helm", "aws", "gcp", "azure",
    "ci/cd", "observability", "prometheus", "grafana", "linux sysadmin", "distributed systems"
]

RELOCATION_KEYWORDS = [
    "relocation", "visa sponsorship", "visa support", "relocate to",
    "visa sponsored", "relocation package", "relocation assistance",
    "willing to relocate", "eu visa", "uk visa", "sponsorship available"
]

EXCLUDE_LOCATIONS = [
    "nigeria only", "lagos only", "africa only"
]


def check_is_relocation(text: str) -> bool:
    """Checks if the opportunity offers relocation or visa sponsorship."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in RELOCATION_KEYWORDS)


def parse_rss_feed(feed_url: str) -> list:
    """Parses an RSS feed safely with user-agent headers."""
    items = []
    try:
        req = urllib.request.Request(
            feed_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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
                "description": desc_text[:400]
            })
    except Exception as e:
        print(f"Warning: RSS parse error for {feed_url}: {e}")
    return items


def parse_remotive_devops() -> list:
    """Pulls international DevOps / Cloud jobs from Remotive API."""
    items = []
    url = "https://remotive.com/api/remote-jobs?category=devops&limit=15"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ChiefOfStaff-Agent/2.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        for job in data.get("jobs", []):
            title = f"{job.get('title', '')} @ {job.get('company_name', '')} ({job.get('candidate_required_location', 'Worldwide')})"
            url_link = job.get("url", "")
            desc = job.get("description", "")
            # Strip simple HTML tags
            desc_clean = desc.replace("<p>", " ").replace("</p>", " ").replace("<br>", " ")[:350]

            items.append({
                "title": title,
                "url": url_link,
                "description": desc_clean
            })
    except Exception as e:
        print(f"Warning: Remotive API fetch error: {e}")
    return items


def parse_hn_search(query: str) -> list:
    """Queries Hacker News Algolia Search API for stories."""
    items = []
    url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(query)}&tags=story"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ChiefOfStaff-Agent/2.0'})
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
        print(f"Warning: HN search error for '{query}': {e}")
    return items


def trigger_crawlers() -> str:
    """
    Crawls international DevOps roles (US, UK, EU, Global Remote) and flags relocation/visa sponsorship.
    """
    total_scraped = 0
    new_found = 0
    relocation_count = 0
    scraped_items = []

    # 1. Scrape Remote DevOps & Sysadmin from WeWorkRemotely
    scraped_items.extend(
        parse_rss_feed("https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss")
    )
    # 2. Scrape WeWorkRemotely Backend
    scraped_items.extend(
        parse_rss_feed("https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss")
    )
    # 3. Scrape Remotive DevOps (International & US/EU)
    scraped_items.extend(parse_remotive_devops())

    # 4. Scrape Hacker News for Visa / Relocation DevOps Opportunities
    scraped_items.extend(parse_hn_search("devops visa sponsorship"))
    scraped_items.extend(parse_hn_search("relocation software engineer"))

    for item in scraped_items:
        title_lower = item["title"].lower()
        desc_lower = item["description"].lower()
        combined_text = title_lower + " " + desc_lower

        # Filter out local-only restrictions
        if any(loc in combined_text for loc in EXCLUDE_LOCATIONS):
            continue

        # Match DevOps / SRE / Platform / Infrastructure keywords
        matches_devops = any(kw in combined_text for kw in DEVOPS_KEYWORDS)
        is_relocation = check_is_relocation(combined_text)

        if not matches_devops and not is_relocation:
            continue

        total_scraped += 1

        # Classify & add badges
        opp_type = "job"
        title_prefix = ""
        if is_relocation:
            title_prefix = "✈️ [VISA / RELOCATION] "
            relocation_count += 1
        elif "uk" in combined_text or "europe" in combined_text or "germany" in combined_text or "netherlands" in combined_text:
            title_prefix = "🇪🇺 [EU/UK REMOTE] "
        elif "us" in combined_text or "united states" in combined_text:
            title_prefix = "🇺🇸 [US REMOTE] "

        full_title = f"{title_prefix}{item['title']}"

        is_new = db.add_opportunity(
            title=full_title,
            url=item["url"],
            opp_type=opp_type,
            description=item["description"]
        )
        if is_new:
            new_found += 1

    db.log_telemetry(
        event_type="crawler_executed",
        details={
            "total_evaluated": len(scraped_items),
            "matched_devops": total_scraped,
            "relocation_flagged": relocation_count,
            "new_stored": new_found,
            "executed_at": datetime.now().isoformat()
        }
    )

    return (
        f"🤖 **DevOps & International Opportunity Radar Completed**!\n"
        f"- Items Evaluated: {len(scraped_items)}\n"
        f"- DevOps/SRE Matched: {total_scraped}\n"
        f"- ✈️ Relocation / Visa Sponsorship Identified: {relocation_count}\n"
        f"- New Opportunities Stored: {new_found}"
    )


def pull_cached_opportunities(limit: int = 5) -> str:
    """
    Retrieves unread international DevOps and relocation opportunities from SQLite.
    """
    unread = db.get_unread_opportunities(limit=limit)
    if not unread:
        return "✨ **Global DevOps Radar**: No new unread international or relocation roles today."

    output = ["🌐 **Global DevOps & International Relocation Radar**:\n"]
    for idx, opp in enumerate(unread, 1):
        db.update_opportunity_status(opp["id"], "sent")
        output.append(
            f"{idx}. **{opp['title']}**\n"
            f"   - 🔗 *Link*: {opp['url']}\n"
            f"   - 📝 *Snippet*: {opp['description'][:140]}..."
        )

    return "\n".join(output)
