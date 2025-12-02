from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    title: str
    image_path: Optional[str] = None
    source: str
    link: str
    date: Optional[datetime] = None
    country: Optional[str] = None
    language: Optional[str] = None


class NewsResponse(BaseModel):
    country: str
    language: str
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_results: int
    period: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    items: List[NewsItem]
    warnings: List[str] = Field(default_factory=list)
