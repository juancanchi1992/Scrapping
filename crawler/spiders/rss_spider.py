from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import scrapy
import feedparser

# Ensure project root is importable to reuse source definitions and helpers.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.sources import SOURCES  # noqa: E402
from app.scraper import parse_entry_date, parse_entry_image  # noqa: E402
from crawler.items import NewsItem  # noqa: E402


class RssAllSpider(scrapy.Spider):
    name = "rss_all"
    allowed_domains: Iterable[str] = []

    def start_requests(self):
        for source in SOURCES:
            for feed_url in source.feeds:
                yield scrapy.Request(feed_url, meta={"source": source})

    def parse(self, response):
        source = response.meta["source"]
        parsed = feedparser.parse(response.text)
        for entry in parsed.entries:
            link = entry.get("link") or ""
            if not link:
                continue
            yield NewsItem(
                title=entry.get("title") or "(sin título)",
                image_path=parse_entry_image(entry),
                source=source.name,
                link=link,
                date=(parse_entry_date(entry) or None),
                country=source.country,
                language=source.language,
            )
