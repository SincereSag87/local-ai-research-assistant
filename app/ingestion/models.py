from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SourceType = Literal["static", "browser"]


class Link(BaseModel):
    text: str
    url: HttpUrl


class WebDocument(BaseModel):
    url: HttpUrl
    final_url: HttpUrl
    title: str | None = None
    text: str = Field(default="")
    links: list[Link] = Field(default_factory=list)
    description: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    source_type: SourceType
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status_code: int | None = None
