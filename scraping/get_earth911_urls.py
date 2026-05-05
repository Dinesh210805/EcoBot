"""
Collect all recycling guide URLs from earth911.com via their XML sitemap.
Falls back to listing page scraping if the sitemap is unavailable.

Run: python scraping/get_earth911_urls.py
Output: data/raw/earth911_urls.json
"""
import asyncio
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "earth911_urls.json"

SITEMAP_INDEX = "https://earth911.com/sitemap_index.xml"
LISTING_BASE = "https://earth911.com/recycling-guide/"
ARTICLE_RE = re.compile(r"https://earth911\.com/recycling-guide/how-to-recycle-[a-z0-9\-]+/?")
MAX_PAGES = 30
REQUEST_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Strategy 1 — XML Sitemap (fast, reliable, no JS rendering needed)
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_sitemap_urls() -> list[str]:
    """Parse earth911 sitemap index → find recycling-guide sitemap → extract URLs."""
    print("Trying sitemap approach…")
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
        # Fetch sitemap index
        try:
            resp = client.get(SITEMAP_INDEX)
            resp.raise_for_status()
        except Exception as e:
            print(f"  Sitemap index failed: {e}")
            return []

        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Find child sitemaps that look like recycling-guide sitemaps
        child_sitemaps: list[str] = []
        for loc in root.findall(".//sm:loc", ns):
            url = loc.text or ""
            if url:
                child_sitemaps.append(url)

        print(f"  Found {len(child_sitemaps)} child sitemaps in index")

        # Collect article URLs from all child sitemaps
        all_urls: list[str] = []
        for sitemap_url in child_sitemaps:
            try:
                r = client.get(sitemap_url)
                r.raise_for_status()
                sm_root = ET.fromstring(r.content)
                for loc in sm_root.findall(".//sm:loc", ns):
                    url = (loc.text or "").rstrip("/")
                    if ARTICLE_RE.match(url + "/") or ARTICLE_RE.match(url):
                        all_urls.append(url)
            except Exception as e:
                print(f"  Skipping {sitemap_url}: {e}")
                continue

    return list(set(all_urls))


# ---------------------------------------------------------------------------
# Strategy 2 — Listing page scraping (fallback)
# ---------------------------------------------------------------------------

async def scrape_listing_page(crawler: AsyncWebCrawler, page: int) -> list[str]:
    url = LISTING_BASE if page == 1 else f"{LISTING_BASE}page/{page}/"
    config = CrawlerRunConfig(
        page_timeout=60000,
        verbose=False,
        headers=HEADERS,
    )
    result = await crawler.arun(url=url, config=config)
    if not result.success:
        print(f"  Crawl failed: {result.error_message}")
        return []

    # Try result.links (Crawl4AI's extracted link list) first
    urls: set[str] = set()
    if result.links:
        for link_dict in result.links.get("internal", []):
            href = link_dict.get("href", "")
            if ARTICLE_RE.match(href):
                urls.add(href.rstrip("/"))

    # Fallback: regex over raw HTML
    if not urls:
        html = result.html or result.cleaned_html or ""
        for match in ARTICLE_RE.finditer(html):
            urls.add(match.group(0).rstrip("/"))

    return list(urls)


async def scrape_listing_pages() -> list[str]:
    print("Falling back to listing page scraping…")
    all_urls: set[str] = set()
    browser_cfg = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for page in range(1, MAX_PAGES + 1):
            print(f"  Page {page}/{MAX_PAGES}…", end=" ", flush=True)
            new_urls = await scrape_listing_page(crawler, page)

            if not new_urls:
                print("empty — stopping")
                break

            before = len(all_urls)
            all_urls.update(new_urls)
            added = len(all_urls) - before
            print(f"{added} new (total: {len(all_urls)})")

            if added == 0:
                print("  No new URLs — last page reached")
                break

            await asyncio.sleep(2)

    return list(all_urls)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing URLs for resumability
    existing: set[str] = set()
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = set(json.load(f))
        print(f"Resuming — {len(existing)} URLs already on disk")

    # Strategy 1: sitemap
    urls = fetch_sitemap_urls()

    # Strategy 2: fallback listing scraper
    if not urls:
        print("Sitemap returned 0 URLs — trying listing page scraper")
        urls = await scrape_listing_pages()

    if not urls:
        print("\nERROR: Could not collect any URLs. earth911.com may be blocking requests.")
        print("Consider running the scraper with a VPN or waiting a few minutes before retrying.")
        sys.exit(1)

    all_urls = existing | set(urls)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(sorted(all_urls), f, indent=2)

    added = len(all_urls) - len(existing)
    print(f"\nDone — {len(all_urls)} total URLs ({added} new)")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
