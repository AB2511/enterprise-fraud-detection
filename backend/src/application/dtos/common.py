"""Common DTOs for pagination, sorting, and filtering."""

from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class SortDirection(str, Enum):
    """Sort direction enumeration."""

    ASC = "asc"
    DESC = "desc"


class SortRequest(BaseModel):
    """Sort request DTO."""

    field: str = Field(..., description="Field to sort by")
    direction: SortDirection = Field(
        default=SortDirection.ASC,
        description="Sort direction (asc or desc)",
    )

    model_config = {"use_enum_values": True}


class PageRequest(BaseModel):
    """Pagination request DTO."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=1000, description="Items per page")
    sort_by: str | None = Field(default=None, description="Field to sort by")
    sort_direction: SortDirection = Field(
        default=SortDirection.ASC,
        description="Sort direction",
    )

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        """Validate page number."""
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """Validate page size."""
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 1000:
            raise ValueError("Page size must be <= 1000")
        return v

    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit (same as page_size)."""
        return self.page_size

    model_config = {"use_enum_values": True}


class PageResponse(BaseModel, Generic[T]):
    """Paginated response DTO."""

    items: list[T] = Field(..., description="List of items in current page")
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page_request: PageRequest,
    ) -> "PageResponse[T]":
        """Create paginated response from items and page request.

        Args:
            items: List of items for current page
            total: Total number of items
            page_request: Original page request

        Returns:
            PageResponse instance
        """
        total_pages = (total + page_request.page_size - 1) // page_request.page_size
        has_next = page_request.page < total_pages
        has_previous = page_request.page > 1

        return cls(
            items=items,
            total=total,
            page=page_request.page,
            page_size=page_request.page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
        )


class FilterRequest(BaseModel):
    """Generic filter request DTO."""

    field: str = Field(..., description="Field to filter on")
    operator: str = Field(..., description="Filter operator (eq, ne, gt, lt, in, like)")
    value: Any = Field(..., description="Filter value")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Validate filter operator."""
        allowed_operators = ["eq", "ne", "gt", "gte", "lt", "lte", "in", "like", "ilike"]
        if v not in allowed_operators:
            raise ValueError(f"Operator must be one of: {allowed_operators}")
        return v
