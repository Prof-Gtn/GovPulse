"""
GovPulse — News Scraper
Scrapes headlines from multiple Namibian news sites.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import urllib3

# NBC's SSL certificate is self-signed. We suppress the warning globally
# but only use verify=False on NBC explicitly (see scrape_nbc_digital).
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

        for article in soup.find_all("article"):
            headline_tag = article.find("h2") or article.find("h3") or article.find("h4")
            link_tag = article.find("a", href=True)

            if not headline_tag or not link_tag:
                continue

            headline = headline_tag.get_text(strip=True)
            if not headline or len(headline) < 15:
                continue

            url_full = link_tag["href"]
            if url_full.startswith("/"):
                url_full = "https://www.namibian.com.na" + url_full

            stories.append({
                "source": "The Namibian",
                "headline": headline,
                "url": url_full,
                "scraped_at": datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"[ERROR] The Namibian: {e}")

    return stories


# ------------------------------------------------------------------
# NEW ERA
# ------------------------------------------------------------------
def scrape_newera():
    """Scrape New Era Live homepage."""
    url = "https://neweralive.na/"
    stories = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        for article in soup.find_all("article"):
            classes = article.get("class", [])
            if not any("cmsmasters_post" in c for c in classes):
                continue

            title_tag = article.find("h3", class_="entry-title") or article.find("h2")
            if not title_tag:
                continue

            link_tag = title_tag.find("a", href=True)
            if not link_tag:
                continue

            headline = link_tag.get_text(strip=True)
            if not headline or len(headline) < 15:
                continue

            url_full = link_tag["href"]
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
# NAMIBIAN SUN
# ------------------------------------------------------------------
def scrape_namibian_sun():
    """
    Scrape headlines from Namibian Sun (namibiansun.com).
    The site has a self-signed SSL cert in its chain, so we use verify=False.
    """
    url = "https://www.namibiansun.com/"
    stories = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=30, verify=False)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as e:
        print(f"[ERROR] Namibian Sun: {e}")
        return []

    # Primary: article containers with a headline + link
    for article in soup.find_all("article"):
        headline_el = article.find("h2") or article.find("h3") or article.find("h4")
        link_el = article.find("a", href=True)

        if not headline_el or not link_el:
            continue

        headline = headline_el.get_text(strip=True)
        if not headline or len(headline) < 15:
            continue

        href = link_el["href"]
        if href.startswith("/"):
            href = "https://www.namibiansun.com" + href

        stories.append({
            "source": "Namibian Sun",
            "headline": headline,
            "url": href,
            "scraped_at": datetime.now().isoformat(),
        })

    # Fallback: anchors with long text pointing to sun.com articles
    if not stories:
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]

            if (
                len(text) > 30
                and "namibiansun.com" in href
                and ("/news/" in href or "/article/" in href or href.count("/") >= 4)
            ):
                stories.append({
                    "source": "Namibian Sun",
                    "headline": text,
                    "url": href,
                    "scraped_at": datetime.now().isoformat(),
                })

    return stories


# ------------------------------------------------------------------
# WINDHOEK OBSERVER
# ------------------------------------------------------------------
def scrape_windhoek_observer():
    """
    Scrape headlines from Windhoek Observer (observer24.com.na).

    The site structures headlines under <h2>/<h3> tags, some with
    nested <a> links. Headlines may be inside <a href="..."> which
    are then wrapped in <h2>/<h3>.
    """
    url = "https://observer24.com.na/"
    stories = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as e:
        print(f"[ERROR] Windhoek Observer: {e}")
        return []

    seen_headlines = set()

    # The page uses <h2> and <h3> tags for headlines.
    # Every headline has an <a> link inside (or wrapped by).
    for heading in soup.find_all(["h2", "h3"]):
        # Try to find the link inside the heading first
        link = heading.find("a", href=True)

        # If the heading itself is inside a link
        if not link:
            parent = heading.parent
            if parent and parent.name == "a" and parent.get("href"):
                link = parent

        if not link:
            continue

        headline = heading.get_text(strip=True)
        if not headline or len(headline) < 20:
            continue

        # Skip navigation/utility headings
        if headline.lower() in {"top stories", "national", "money", "sport", "opinion", "world", "business"}:
            continue

        # Skip duplicates (same headline appears in multiple sections)
        key = headline.lower()
        if key in seen_headlines:
            continue
        seen_headlines.add(key)

        href = link["href"]
        if href.startswith("/"):
            href = "https://observer24.com.na" + href
        elif not href.startswith("http"):
            href = "https://observer24.com.na/" + href.lstrip("/")

        stories.append({
            "source": "Windhoek Observer",
            "headline": headline,
            "url": href,
            "scraped_at": datetime.now().isoformat(),
        })

    # Fallback: anchors with long text
    if not stories:
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]

            if (
                len(text) > 30
                and "observer24.com.na" in href
                and href.count("/") >= 4
            ):
                key = text.lower()
                if key in seen_headlines:
                    continue
                seen_headlines.add(key)

                stories.append({
                    "source": "Windhoek Observer",
                    "headline": text,
                    "url": href,
                    "scraped_at": datetime.now().isoformat(),
                })

    return stories


# ------------------------------------------------------------------
# NBC DIGITAL
# ------------------------------------------------------------------
def scrape_nbc_digital():
    """
    Scrape NBC Digital news section.

    NOTE: NBC's SSL certificate is misconfigured (self-signed chain).
    We use verify=False here deliberately. We flag this to the user
    and skip gracefully if the site is unreachable.
    """
    url = "https://www.nbc.na/news"
    stories = []

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            verify=False,   # NBC's cert chain is broken
        )
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        for article in soup.find_all("article"):
            headline_tag = article.find("h2") or article.find("h3") or article.find("h4")
            link_tag = article.find("a", href=True)

            if not headline_tag or not link_tag:
                continue

            headline = headline_tag.get_text(strip=True)
            if not headline or len(headline) < 15:
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
        print(f"[WARN] NBC Digital unavailable — SSL issue on their end: {e}")

    return stories


# ------------------------------------------------------------------
# ARTICLE BODY FETCHER
# ------------------------------------------------------------------
def fetch_article_body(url):
    """Fetch the full article text from a story page."""
    try:
        # NBC has a broken cert, use verify=False for it
        verify = "nbc.na" not in url

        response = requests.get(url, headers=HEADERS, timeout=15, verify=verify)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "lxml")

        body_div = (
            soup.find("div", class_="entry-content")
            or soup.find("div", class_="cmsmasters_post_content")
            or soup.find("div", class_="td-post-content")
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

    print("[3/4] Scraping Namibian Sun...")
    sun = scrape_namibian_sun()
    print(f"      Found {len(sun)}")
    all_stories.extend(sun)

    print("[4/4] Scraping Windhoek Observer...")
    obs = scrape_windhoek_observer()
    print(f"      Found {len(obs)}")
    all_stories.extend(obs)

    # Deduplicate by headline (some sites repost wire content)
    seen = set()
    unique = []
    for s in all_stories:
        key = s.get("headline", "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(s)

    print(f"\n      Total unique stories: {len(unique)}")

    print(f"\n[+] Fetching full text for {len(unique)} stories (parallel)...")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(idx_story):
        idx, story = idx_story
        print(f"      [{idx}/{len(unique)}] {story['headline'][:60]}...")
        story["body"] = fetch_article_body(story["url"])
        return story

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_fetch_one, (i, s)) for i, s in enumerate(unique, 1)]
        for f in as_completed(futures):
            f.result()

    return unique


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