from __future__ import annotations

from datetime import date
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, Query

from .schemas import NewsResponse
from .scraper import fetch_news
from .sources import SUPPORTED_COUNTRIES

app = FastAPI(
    title="Scraping News API",
    description="Aggregates news by country, language, and date ranges with RSS-based scraping.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "supported_countries": SUPPORTED_COUNTRIES}


@app.get("/news", response_model=NewsResponse)
async def get_news(
    q: str = Query(..., description="Keyword obligatorio para buscar noticias"),
    country: Optional[str] = Query(None, description="Country code like es-AR, es-CO, es-ES, en-US"),
    language: Optional[str] = Query(None, description="Two-letter language code. If omitted, no language filter when country not provided."),
    period: Optional[Literal["day", "week", "month", "year"]] = Query(
        None, description="Rango relativo: day, week, month o year. Alternativa a date_from/date_to."
    ),
    date_from: Optional[date] = Query(None, description="ISO date lower bound"),
    date_to: Optional[date] = Query(None, description="ISO date upper bound"),
    page: int = Query(1, ge=1),
    page_size: int = Query(..., ge=1, le=100, description="Total de items a devolver por página (obligatorio)"),
    debug: bool = Query(False, description="Si true, devuelve URLs de feeds en warnings"),
) -> NewsResponse:
    try:
        items, warnings, total, resolved_country, feed_urls = await fetch_news(
            keyword=q,
            country=country,
            language=language,
            period=period,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    resolved_language = language or (items[0].language if items else None)

    return NewsResponse(
        country=resolved_country,
        language=resolved_language or "",
        page=page,
        page_size=page_size,
        total_results=total,
        period=period,
        date_from=date_from,
        date_to=date_to,
        items=items,
        warnings=(warnings + [f"feeds: {', '.join(feed_urls)}"]) if debug else warnings,
    )
