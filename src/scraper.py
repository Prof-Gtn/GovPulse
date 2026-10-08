"""
GovPulse — News Scraper
Scrapes headlines from The Namibian homepage, then fetches full article text.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import time


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def scrape_homepage():
    """Get headlines and URLs from The Namibian homepage."""
    url = "https://www.namibian.com.na/"
    stories = []

    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "lxml")

    for article in soup.find_all("article", limit=20):
        headline_tag = article.find("h2") or article.find("h3") or article.find("h4")
        link_tag = article.find("a", href=True)

        if not headline_tag or not link_tag:
            continue

        stories.append({
            "source": "The Namibian",
            "headline": headline_tag.get_text(strip=True),
            "url": link_tag["href"],
            "scraped_at": datetime.now().isoformat(),
        })

    return stories


def fetch_article_body(url):
    """Visit an article page and extract the full body text."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        # The article body wrapper (from DevTools inspection)
        body_div = soup.find("div", class_="entry-content")
        if not body_div:
            return ""

        # Get all paragraphs inside the body
        paragraphs = body_div.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs)

        return text

    except Exception as e:
        print(f"    [WARN] Could not fetch {url}: {e}")
        return ""


def scrape_all():
    """Scrape homepage, then fetch full text for each article."""
    print("[1/2] Scraping homepage...")
    stories = scrape_homepage()
    print(f"      Found {len(stories)} stories\n")

    print("[2/2] Fetching full article text...")
    for i, story in enumerate(stories, 1):
        print(f"      [{i}/{len(stories)}] {story['headline'][:60]}...")
        story["body"] = fetch_article_body(story["url"])
        time.sleep(0.5)  # Be polite — don't hammer the server

    return stories


def save_stories(stories, filename="data/raw/stories.json"):
    """Save scraped stories to a JSON file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8-sig") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)

    # Report on body text success
    with_body = sum(1 for s in stories if s.get("body"))
    print(f"\n[OK] Saved {len(stories)} stories ({with_body} with full text) → {filename}")


if __name__ == "__main__":
    stories = scrape_all()
    save_stories(stories)

    print("\nSample:")
    for s in stories[:3]:
        print(f"\n  Headline: {s['headline']}")
        print(f"  Body: {s['body'][:150]}...")