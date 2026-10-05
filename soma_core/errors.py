"""Standardized typed exception hierarchy for Soma-Governance."""
from __future__ import annotations

from typing import Any, Optional


class SomaError(Exception):
    """Root domain exception for all soma operations."""

    def __init__(self, message: str = "", code: str = "ERR_SOMA", **kwargs: Any) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self) -> str:
        return self.message if self.message else super().__str__()


class SomaValidationError(SomaError, ValueError):
    """Raised when data validation fails against Soma contracts or schemas."""

    def __init__(self, message: str = "", code: str = "VALIDATION_ERROR", **kwargs: Any) -> None:
        super().__init__(message, code=code, **kwargs)


class CellCorruptError(SomaError):
    """Raised when a cell frontmatter or body is malformed or unparseable."""

    def __init__(
        self,
        message: str = "",
        cell_id: Optional[str] = None,
        code: str = "CELL_CORRUPT",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, cell_id=cell_id, **kwargs)
        self.cell_id = cell_id


class ReceiptExpiredError(SomaError, KeyError):
    """Raised when a receipt is expired or not found."""

    def __init__(
        self,
        message: str = "",
        receipt_id: Optional[str] = None,
        code: str = "RECEIPT_EXPIRED",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, receipt_id=receipt_id, **kwargs)
        self.receipt_id = receipt_id


class LockTimeoutError(SomaError, TimeoutError):
    """Raised when a workspace lock cannot be acquired within the timeout period."""

    def __init__(
        self,
        message: str = "",
        resource: Optional[str] = None,
        code: str = "LOCK_TIMEOUT",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, code=code, resource=resource, **kwargs)
        self.resource = resource


__all__ = [
    "CellCorruptError",
    "LockTimeoutError",
    "ReceiptExpiredError",
    "SomaError",
    "SomaValidationError",
]

