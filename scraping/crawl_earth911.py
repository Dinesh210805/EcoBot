"""
Crawl earth911 recycling guide articles using Crawl4AI.
Reads URL list from data/raw/earth911_urls.json, skips already-scraped pages,
and saves each article as data/raw/earth911/<slug>.md.

Run: python scraping/crawl_earth911.py
     python scraping/crawl_earth911.py --limit 50   # partial run
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

URLS_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "earth911_urls.json"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "earth911"

BATCH_SIZE = 5
BATCH_DELAY = 2.0  # seconds between batches (polite crawling)


def url_to_slug(url: str) -> str:
    match = re.search(r"/how-to-recycle-([a-z0-9\-]+)/?$", url)
    return match.group(1) if match else re.sub(r"[^a-z0-9\-]", "-", url.split("/")[-1])


async def crawl_one(crawler: AsyncWebCrawler, url: str) -> str | None:
    config = CrawlerRunConfig(
        page_timeout=30000,
        wait_for="css:article, css:.entry-content, css:.post-content",
        remove_overlay_elements=True,
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        verbose=False,
    )
    result = await crawler.arun(url=url, config=config)
    if not result.success:
        print(f"  FAIL {url}: {result.error_message}")
        return None
    return result.markdown or result.cleaned_html or ""


async def crawl_batch(crawler: AsyncWebCrawler, batch: list[str]) -> dict[str, str]:
    tasks = [crawl_one(crawler, url) for url in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {url: res for url, res in zip(batch, results) if isinstance(res, str) and res}


async def main(limit: int | None = None) -> None:
    if not URLS_FILE.exists():
        print(f"URL list not found: {URLS_FILE}")
        print("Run scraping/get_earth911_urls.py first.")
        sys.exit(1)

    with open(URLS_FILE) as f:
        all_urls: list[str] = json.load(f)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Skip already-scraped slugs
    existing_slugs = {p.stem for p in OUTPUT_DIR.glob("*.md")}
    pending = [u for u in all_urls if url_to_slug(u) not in existing_slugs]

    if limit:
        pending = pending[:limit]

    print(f"URLs total: {len(all_urls)}  |  already scraped: {len(existing_slugs)}  |  pending: {len(pending)}")

    browser_cfg = BrowserConfig(headless=True, verbose=False)
    saved = 0
    failed = 0

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start : batch_start + BATCH_SIZE]
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"Batch {batch_num}/{total_batches}  ({batch_start + 1}–{min(batch_start + BATCH_SIZE, len(pending))})")

            results = await crawl_batch(crawler, batch)

            for url, markdown in results.items():
                slug = url_to_slug(url)
                out_path = OUTPUT_DIR / f"{slug}.md"
                content = f"<!-- source: {url} -->\n\n{markdown}"
                out_path.write_text(content, encoding="utf-8")
                saved += 1

            failed += len(batch) - len(results)

            if batch_start + BATCH_SIZE < len(pending):
                await asyncio.sleep(BATCH_DELAY)

    print(f"\nDone — saved: {saved}  |  failed: {failed}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max articles to scrape (for testing)")
    args = parser.parse_args()
    asyncio.run(main(limit=args.limit))
