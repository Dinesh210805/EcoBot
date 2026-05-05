"""
Fetch CPCB government documents using Crawl4AI (HTML pages) and pdfplumber (PDF URLs).
No API key required — fully open source.

Run: python scraping/crawl_cpcb.py
     python scraping/crawl_cpcb.py --source swm_rules_2016  # single source
Output: data/raw/cpcb_pdfs/<name>.md
"""
import argparse
import asyncio
import io
import sys
import time
from pathlib import Path

import httpx
import pdfplumber
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraping.cpcb_sources import CPCB_SOURCES

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "cpcb_pdfs"
REQUEST_DELAY = 3.0  # seconds between requests — polite crawling of gov sites
PDF_DOWNLOAD_TIMEOUT = 60  # seconds


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber."""
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def fetch_pdf(url: str) -> str | None:
    """Download a PDF and extract its text content."""
    try:
        with httpx.Client(follow_redirects=True, timeout=PDF_DOWNLOAD_TIMEOUT, verify=False) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (research bot)"})
            resp.raise_for_status()
            return extract_pdf_text(resp.content)
    except httpx.HTTPStatusError as e:
        print(f"  HTTP {e.response.status_code} fetching PDF: {url}")
        return None
    except Exception as e:
        print(f"  PDF extraction error: {e}")
        return None


async def fetch_html(url: str) -> str | None:
    """Scrape an HTML page using Crawl4AI."""
    config = CrawlerRunConfig(
        page_timeout=60000,
        remove_overlay_elements=True,
        excluded_tags=["nav", "footer", "header", "aside", "script", "style"],
        verbose=False,
    )
    browser_cfg = BrowserConfig(headless=True, verbose=False)
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=config)
        if not result.success:
            err = (result.error_message or "").encode("ascii", errors="replace").decode("ascii")
            print(f"  Crawl4AI error: {err}")
            return None
        return result.markdown or result.cleaned_html or ""


async def fetch_source(source: dict) -> str | None:
    if source["type"] == "pdf":
        return fetch_pdf(source["url"])
    return await fetch_html(source["url"])


async def main(only_source: str | None = None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sources = CPCB_SOURCES
    if only_source:
        sources = [s for s in CPCB_SOURCES if s["name"] == only_source]
        if not sources:
            print(f"Source '{only_source}' not found in cpcb_sources.py")
            sys.exit(1)

    saved = skipped = failed = 0

    for i, source in enumerate(sources, 1):
        out_path = OUTPUT_DIR / f"{source['name']}.md"

        if out_path.exists():
            print(f"[{i}/{len(sources)}] SKIP {source['name']} (already exists)")
            skipped += 1
            continue

        print(f"[{i}/{len(sources)}] {source['name']} [{source['type']}] — {source['description']}")
        content = await fetch_source(source)

        if content and content.strip():
            header = (
                f"<!-- source: {source['url']} -->\n"
                f"<!-- type: {source['type']} -->\n"
                f"<!-- description: {source['description']} -->\n\n"
            )
            out_path.write_text(header + content, encoding="utf-8")
            print(f"  Saved {len(content):,} chars -> {out_path.name}")
            saved += 1
        else:
            print(f"  No content extracted — skipping")
            failed += 1

        if i < len(sources):
            await asyncio.sleep(REQUEST_DELAY)

    print(f"\nDone — saved: {saved}  |  skipped: {skipped}  |  failed: {failed}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None, help="Fetch a single source by name")
    args = parser.parse_args()
    asyncio.run(main(only_source=args.source))
