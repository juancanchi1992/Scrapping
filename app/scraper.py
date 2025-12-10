from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

import feedparser
import httpx
from dateutil import parser as date_parser
from urllib.parse import quote_plus
import unicodedata
import re

from .schemas import NewsItem
from .sources import NewsSource, sources_for_country, SUPPORTED_COUNTRIES, active_sources
from .manual_sources import manual_sources_for_country


COUNTRY_ALIASES: Dict[str, str] = {
    "es": "es-ES",
    "es-es": "es-ES",
    "es-esp": "es-ES",
    "spain": "es-ES",
    "ar": "es-AR",
    "arg": "es-AR",
    "argentina": "es-AR",
    "es-ar": "es-AR",
    "co": "es-CO",
    "col": "es-CO",
    "colombia": "es-CO",
    "es-co": "es-CO",
    "mx": "es-MX",
    "mex": "es-MX",
    "mexico": "es-MX",
    "es-mx": "es-MX",
    "pe": "es-PE",
    "peru": "es-PE",
    "es-pe": "es-PE",
    "cl": "es-CL",
    "chile": "es-CL",
    "es-cl": "es-CL",
    "ec": "es-EC",
    "ecuador": "es-EC",
    "es-ec": "es-EC",
    "ve": "es-VE",
    "venezuela": "es-VE",
    "es-ve": "es-VE",
    "us": "en-US",
    "usa": "en-US",
    "eeuu": "en-US",
    "en-us": "en-US",
    "us-en": "en-US",
}


def normalize_country(country: str) -> str:
    key = country.strip().lower()
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    if country in SUPPORTED_COUNTRIES:
        return country
    raise ValueError(f"Unsupported country '{country}'. Supported: {', '.join(SUPPORTED_COUNTRIES)}")


def normalize_language(lang: Optional[str], country_sources: List[NewsSource]) -> str:
    if lang:
        return lang.split("-")[0].lower()
    return country_sources[0].language


def date_range_from_period(period: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
    if not period:
        return None, None
    period = period.lower()
    today = datetime.utcnow().date()
    if period == "day":
        return today - timedelta(days=1), today
    if period == "week":
        return today - timedelta(days=7), today
    if period == "month":
        return today - timedelta(days=30), today
    if period == "year":
        return today - timedelta(days=365), today
    raise ValueError("Period must be one of: day, week, month, year")


def parse_entry_date(entry) -> Optional[datetime]:
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6])
    for attr in ("published", "updated", "pubDate"):
        raw = entry.get(attr)
        if raw:
            try:
                return date_parser.parse(raw)
            except (ValueError, TypeError):
                continue
    return None


def parse_entry_image(entry) -> Optional[str]:
    # Try media:content
    media_content = entry.get("media_content") or entry.get("media:content") or []
    if isinstance(media_content, dict):
        media_content = [media_content]
    if media_content:
        url = media_content[0].get("url")
        if url:
            return url
    # Try media:thumbnail
    media_thumbnail = entry.get("media_thumbnail") or entry.get("media:thumbnail") or []
    if isinstance(media_thumbnail, dict):
        media_thumbnail = [media_thumbnail]
    if media_thumbnail:
        url = media_thumbnail[0].get("url")
        if url:
            return url
    # Enclosures
    enclosures = entry.get("enclosures") or []
    for enc in enclosures:
        url = enc.get("href") or enc.get("url")
        if url:
            mime = (enc.get("type") or "").lower()
            if "image" in mime or mime.endswith(("jpg", "jpeg", "png", "webp")):
                return url
    # Some feeds put image in content
    content = entry.get("content") or []
    if content and isinstance(content, list):
        for c in content:
            val = c.get("value") or ""
            if "img" in val and "src=" in val:
                m = re.search(r'src=[\"\\\']([^\"\\\']+)', val)
                if m:
                    return m.group(1)
    return None


def extract_og_image(html: str) -> Optional[str]:
    patterns = [
        r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
        r'<meta[^>]+name=[\'"]twitter:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
        r'<meta[^>]+property=[\'"]og:image:secure_url[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def normalize_text(text: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return normalized


async def fetch_feed(
    client: httpx.AsyncClient, source: NewsSource, feed_url: str, keyword_lower: Optional[str]
) -> Tuple[List[NewsItem], Optional[str]]:
    try:
        resp = await client.get(
            feed_url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (NewsScraper; +https://example.com)"},
        )
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
    except Exception as exc:
        return [], f"{source.name} feed failed ({feed_url}): {exc}"

    items: List[NewsItem] = []
    for entry in parsed.entries:
        published_at = parse_entry_date(entry) if hasattr(entry, "get") else None
        summary = entry.get("summary") or entry.get("description") or ""
        link = entry.get("link") or ""
        if not link:
            continue
        image = parse_entry_image(entry)
        source_title = (
            (entry.get("source") or {}).get("title")
            if isinstance(entry.get("source"), dict)
            else None
        ) or source.name
        if keyword_lower:
            searchable = normalize_text(f"{entry.get('title','')} {summary} {source_title}")
            if keyword_lower not in searchable:
                continue
        items.append(
            NewsItem(
                title=entry.get("title") or "(sin título)",
                link=link,
                image_path=image,
                date=published_at,
                source=source_title,
                country=source.country,
                language=source.language,
            )
        )
    return items, None


async def fetch_news(
    keyword: str,
    country: Optional[str],
    language: Optional[str],
    period: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
    page: int,
    page_size: int,
) -> Tuple[List[NewsItem], List[str], int, str, List[str]]:
    normalized_country = normalize_country(country) if country else None
    if normalized_country:
        sources = sources_for_country(normalized_country)
        if not sources:
            raise ValueError(f"No sources configured for country {normalized_country}")
    else:
        sources = active_sources()

    if language:
        lang = language.split("-")[0].lower()
    elif normalized_country:
        lang = normalize_language(None, sources)
    else:
        lang = None
    warnings: List[str] = []
    feed_urls: List[str] = []
    items: List[NewsItem] = []

    period_from, period_to = date_range_from_period(period)
    effective_from = date_from or period_from
    effective_to = date_to or period_to

    async with httpx.AsyncClient() as client:
        tasks = []
        keyword_lower = normalize_text(keyword)
        for source in sources:
            for feed_url in source.feeds:
                tasks.append(fetch_feed(client, source, feed_url, keyword_lower))
                feed_urls.append(f"{source.id}: {feed_url}")
        # Google News fallback por país o global.
        g_source = NewsSource(
            id="google-news",
            name="Google News",
            country=normalized_country or "all",
            language=lang or (language.split("-")[0].lower() if language else "es"),
            feeds=[google_news_feed(keyword, normalized_country, language or lang)],
            homepage="https://news.google.com",
        )
        tasks.append(fetch_feed(client, g_source, g_source.feeds[0], None))
        feed_urls.append(f"{g_source.id}: {g_source.feeds[0]}")
        results = await asyncio.gather(*tasks)

    # Add manual HTML sources (non-RSS) per country.
    manual_urls = manual_sources_for_country(normalized_country) if normalized_country else []
    if manual_urls:
        manual_items, manual_warnings = await fetch_manual_sources(keyword_lower, manual_urls, lang or "")
        items.extend(manual_items)
        warnings.extend(manual_warnings)
        feed_urls.extend([f"manual: {u}" for u in manual_urls])

    for feed_items, err in results:
        if err:
            warnings.append(err)
        items.extend(feed_items)

    filtered: List[NewsItem] = []
    for item in items:
        if lang and item.language != lang:
            continue
        if effective_from or effective_to:
            if not item.date:
                continue
            item_date = item.date.date()
            if effective_from and item_date < effective_from:
                continue
            if effective_to and item_date > effective_to:
                continue
        filtered.append(item)

    # Deduplicate by link
    seen = set()
    unique_items: List[NewsItem] = []
    for item in filtered:
        if item.link in seen:
            continue
        seen.add(item.link)
        unique_items.append(item)

    unique_items.sort(key=lambda x: x.date or datetime.min, reverse=True)
    total = len(unique_items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = unique_items[start:end]
    await backfill_images(page_items)
    if total > end:
        warnings.append(f"Results truncated from {total} to page slice")
    return page_items, warnings, total, normalized_country or "all", feed_urls


def google_news_feed(keyword: str, country: Optional[str], language: Optional[str]) -> str:
    # Google News RSS supports hl (language), gl (country), ceid (country:lang)
    lang = (language or "es").split("-")[0].lower()
    if country:
        gl = country.split("-")[-1].upper()
        ceid = f"{gl}:{lang}"
    else:
        gl = "US"
        ceid = f"{gl}:{lang}"
    q = quote_plus(keyword)
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={gl}&ceid={ceid}"


async def backfill_images(items: List[NewsItem]) -> None:
    async with httpx.AsyncClient() as client:
        tasks = []
        for item in items:
            if item.image_path and "googleusercontent.com" not in item.image_path:
                continue
            # Try to upgrade images that are google proxy or missing.
            item.image_path = None
            tasks.append(fetch_og_image(client, item))
        if tasks:
            await asyncio.gather(*tasks)


async def fetch_og_image(client: httpx.AsyncClient, item: NewsItem) -> None:
    try:
        # If link is a Google News redirect, resolve first to get final URL.
        target_url = item.link
        if "news.google.com" in target_url:
            try:
                resp0 = await client.get(
                    target_url,
                    timeout=6,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (NewsScraper; +https://example.com)"},
                )
                target_url = str(resp0.url)
            except Exception:
                target_url = item.link

        resp = await client.get(
            target_url,
            timeout=6,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (NewsScraper; +https://example.com)"},
        )
        resp.raise_for_status()
        image = extract_og_image(resp.text)
        if image and "googleusercontent.com" in image:
            image = None
        if not image:
            # Detect meta refresh redirect
            m = re.search(r'http-equiv=["\\\']refresh["\\\'][^>]*url=([^"\\\' >]+)', resp.text, flags=re.IGNORECASE)
            if m:
                try:
                    redirect_url = m.group(1)
                    resp2 = await client.get(
                        redirect_url,
                        timeout=6,
                        follow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0 (NewsScraper; +https://example.com)"},
                    )
                    resp2.raise_for_status()
                    image = extract_og_image(resp2.text)
                    if image and "googleusercontent.com" in image:
                        image = None
                    if image:
                        item.image_path = image
                        return
                except Exception:
                    pass
        if image:
            item.image_path = image
            return
    except Exception:
        return


async def fetch_manual_sources(keyword_lower: str, urls: List[str], language: str) -> Tuple[List[NewsItem], List[str]]:
    items: List[NewsItem] = []
    warnings: List[str] = []
    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                resp = await client.get(
                    url,
                    timeout=8,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (NewsScraper; +https://example.com)"},
                )
                resp.raise_for_status()
                html = resp.text
                title = extract_title(html) or url
                desc = extract_description(html) or ""
                searchable = normalize_text(f"{title} {desc}")
                if keyword_lower not in searchable:
                    continue
                image = extract_og_image(html)
                if image and "googleusercontent.com" in image:
                    image = None
                items.append(
                    NewsItem(
                        title=title,
                        image_path=image,
                        source=url.split("/")[2],
                        link=url,
                        date=None,
                        country="",
                        language=language,
                    )
                )
            except Exception as exc:
                warnings.append(f"Manual source failed ({url}): {exc}")
    return items, warnings


def extract_title(html: str) -> Optional[str]:
    m = re.search(r"<title>([^<]+)</title>", html, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def extract_description(html: str) -> Optional[str]:
    m = re.search(
        r'<meta[^>]+name=["\\\']description["\\\'][^>]+content=["\\\']([^"\\\']+)["\\\']',
        html,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return None
