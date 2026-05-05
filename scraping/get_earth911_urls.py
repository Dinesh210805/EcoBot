"""
Collect all recycling guide URLs from earth911.com listing pages.
Uses Crawl4AI to scrape paginated listing pages and extract article URLs.

Run: python scraping/get_earth911_urls.py
Output: data/raw/earth911_urls.json
"""
import asyncio
import json
import re
import sys
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "earth911_urls.json"

LISTING_BASE = "https://earth911.com/recycling-guide/"
ARTICLE_PATTERN = re.compile(r"/recycling-guide/how-to-recycle-[a-z0-9\-]+/?")

# earth911 paginates their guide listing — 25 per page, ~22 pages as of 2024
MAX_PAGES = 30


async def scrape_listing_page(crawler: AsyncWebCrawler, page: int) -> list[str]:
    url = LISTING_BASE if page == 1 else f"{LISTING_BASE}page/{page}/"
    config = CrawlerRunConfig(
        page_timeout=30000,
        wait_for="css:.entry-title",
        verbose=False,
    )
    result = await crawler.arun(url=url, config=config)
    if not result.success:
        return []

    found = ARTICLE_PATTERN.findall(result.html or "")
    # Normalise: strip trailing slash, deduplicate
    urls = list({f"https://earth911.com{u.rstrip('/')}" for u in found})
    return urls


async def main() -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load already-collected URLs to allow resumable runs
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            all_urls: set[str] = set(json.load(f))
        print(f"Resuming — {len(all_urls)} URLs already collected")
    else:
        all_urls = set()

    browser_cfg = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for page in range(1, MAX_PAGES + 1):
            print(f"Scraping listing page {page}/{MAX_PAGES}…", end=" ", flush=True)
            new_urls = await scrape_listing_page(crawler, page)

            if not new_urls:
                print("empty — stopping")
                break

            before = len(all_urls)
            all_urls.update(new_urls)
            added = len(all_urls) - before
            print(f"{added} new ({len(new_urls)} found)")

            # Persist after every page so a crash doesn't lose progress
            with open(OUTPUT_FILE, "w") as f:
                json.dump(sorted(all_urls), f, indent=2)

            if added == 0:
                # No new URLs on this page — we've likely hit the end
                print("No new URLs — assuming last page reached")
                break

            await asyncio.sleep(2)

    print(f"\nTotal URLs collected: {len(all_urls)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
