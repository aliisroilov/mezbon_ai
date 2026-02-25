import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort: str | None = None
    order: str = Field(default="desc", pattern=r"^(asc|desc)$")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

    def to_meta(self, total: int) -> PaginationMeta:
        return PaginationMeta(
            page=self.page,
            limit=self.limit,
            total=total,
            total_pages=math.ceil(total / self.limit) if self.limit > 0 else 0,
        )


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None
    meta: dict[str, Any] | None = None
