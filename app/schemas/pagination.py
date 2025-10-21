from __future__ import annotations
from typing import Generic, List, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int

class Page(BaseModel, Generic[T]):
    data: List[T]
    meta: PageMeta
