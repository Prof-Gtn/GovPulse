"""
GovPulse — News Scraper
Scrapes headlines from multiple Namibian news sites.
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


# ------------------------------------------------------------------
# THE NAMIBIAN
# ------------------------------------------------------------------
def scrape_namibian():
    """Scrape The Namibian homepage."""
    url = "https://www.namibian.com.na/"
    stories = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
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
    except Exception as e:
        print(f"[ERROR] The Namibian: {e}")

    return stories


# ------------------------------------------------------------------
# NEW ERA  (uses cmsmasters_post_masonry articles with h3.entry-title)
# ------------------------------------------------------------------
def scrape_newera():
    """Scrape New Era Live homepage."""
    url = "https://neweralive.na/"
    stories = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        # New Era wraps each card in <article class="cmsmasters_post_masonry">
        for article in soup.find_all("article", limit=20):
            classes = article.get("class", [])
            if not any("cmsmasters_post" in c for c in classes):
                continue

            # The headline is inside <h3 class="entry-title"><a href="...">...</a></h3>
            title_tag = article.find("h3", class_="entry-title") or article.find("h2")
            if not title_tag:
                continue

            link_tag = title_tag.find("a", href=True)
            if not link_tag:
                continue

            headline = link_tag.get_text(strip=True)
            # Skip very short or empty headlines
            if not headline or len(headline) < 10:
                continue

            url_full = link_tag["href"]
            # Make absolute if relative
            if url_full.startswith("/"):
                url_full = "https://neweralive.na" + url_full

            stories.append({
                "source": "New Era",
                "headline": headline,
                "url": url_full,
                "scraped_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[ERROR] New Era: {e}")

    return stories


# ------------------------------------------------------------------
# NBC DIGITAL
# ------------------------------------------------------------------
def scrape_nbc_digital():
    """Scrape NBC Digital news section."""
    url = "https://www.nbc.na/news"
    stories = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        for article in soup.find_all("article", limit=20):
            headline_tag = article.find("h2") or article.find("h3") or article.find("h4")
            link_tag = article.find("a", href=True)

            if not headline_tag or not link_tag:
                continue

            headline = headline_tag.get_text(strip=True)
            if not headline or len(headline) < 10:
                continue

            url_full = link_tag["href"]
            if url_full.startswith("/"):
                url_full = "https://www.nbc.na" + url_full

            stories.append({
                "source": "NBC Digital",
                "headline": headline,
                "url": url_full,
                "scraped_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[ERROR] NBC Digital: {e}")

    return stories


# ------------------------------------------------------------------
# ARTICLE BODY FETCHER (multi-site)
# ------------------------------------------------------------------
def fetch_article_body(url):
    """Fetch the full article text from a story page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        # Multiple body patterns across sites
        body_div = (
            soup.find("div", class_="entry-content")
            or soup.find("div", class_="cmsmasters_post_content")
            or soup.find("article")
        )

        if not body_div:
            return ""

        paragraphs = body_div.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs)
        return text[:5000]
    except Exception as e:
        print(f"    [WARN] Body fetch failed: {e}")
        return ""


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------
def scrape_all():
    """Scrape all sources and fetch full text for each story."""
    all_stories = []

    print("[1/4] Scraping The Namibian...")
    nam = scrape_namibian()
    print(f"      Found {len(nam)}")
    all_stories.extend(nam)

    print("[2/4] Scraping New Era...")
    ne = scrape_newera()
    print(f"      Found {len(ne)}")
    all_stories.extend(ne)

    print("[3/4] Scraping NBC Digital...")
    nbc = scrape_nbc_digital()
    print(f"      Found {len(nbc)}")
    all_stories.extend(nbc)

    print(f"\n[4/4] Fetching full text for {len(all_stories)} stories...")
    for i, story in enumerate(all_stories, 1):
        print(f"      [{i}/{len(all_stories)}] {story['headline'][:60]}...")
        story["body"] = fetch_article_body(story["url"])
        time.sleep(0.5)

    return all_stories


def save_stories(stories, filename="data/raw/stories.json"):
    """Save scraped stories to JSON."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(stories, f, indent=2, ensure_ascii=False)

    with_body = sum(1 for s in stories if s.get("body"))
    print(f"\n[OK] Saved {len(stories)} stories ({with_body} with full text) -> {filename}")


if __name__ == "__main__":
    stories = scrape_all()
    save_stories(stories)