"""
Modern exception handling for the DuckDuckGo search plugin.

This module provides structured exception types and exception groups
for better error handling and debugging in Python 3.11+.
"""

import sys
from typing import Any


class DuckDuckGoError(Exception):
    """Base exception for DuckDuckGo search errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class SearchError(DuckDuckGoError):
    """Error during search operation."""

    pass


class NetworkError(DuckDuckGoError):
    """Network-related error."""

    pass


class ParseError(DuckDuckGoError):
    """Error parsing search results or web content."""

    pass


class ValidationError(DuckDuckGoError):
    """Error validating search parameters or results."""

    pass


class ContentExtractionError(DuckDuckGoError):
    """Error extracting content from web pages."""

    pass


# Modern exception groups for Python 3.11+
if sys.version_info >= (3, 11):
    # These will be properly imported in Python 3.11+
    from builtins import ExceptionGroup  # type: ignore

    class SearchExceptionGroup(ExceptionGroup):
        """Group of search-related exceptions."""

        pass

    class ValidationExceptionGroup(ExceptionGroup):
        """Group of validation-related exceptions."""

        pass

    class NetworkExceptionGroup(ExceptionGroup):
        """Group of network-related exceptions."""

        pass
else:  # pragma: no cover - Python 3.11+ only path exercised in tests
    # Fallback for older Python versions
    class SearchExceptionGroup(Exception):
        """Fallback exception group for older Python versions."""

        def __init__(self, message: str, exceptions: list[Exception]):
            super().__init__(message)
            self.exceptions = exceptions

    class ValidationExceptionGroup(Exception):
        """Fallback exception group for older Python versions."""

        def __init__(self, message: str, exceptions: list[Exception]):
            super().__init__(message)
            self.exceptions = exceptions

    class NetworkExceptionGroup(Exception):
        """Fallback exception group for older Python versions."""

        def __init__(self, message: str, exceptions: list[Exception]):
            super().__init__(message)
            self.exceptions = exceptions


def handle_multiple_errors(errors: list[Exception], context: str = "") -> None:
    """
    Handle multiple errors using exception groups.

    In Python 3.11+, uses native ExceptionGroup.
    For older versions, raises the first error with context.
    """
    if not errors:
        return

    if len(errors) == 1:
        raise errors[0]

    if sys.version_info >= (3, 11):
        # Use native exception groups
        from builtins import ExceptionGroup  # type: ignore

        message = f"Multiple errors occurred{f' in {context}' if context else ''}"
        raise ExceptionGroup(message, errors)
    else:  # pragma: no cover - fallback for unsupported interpreter versions
        # Fallback: raise first error with context about others
        first_error = errors[0]
        other_errors = [str(e) for e in errors[1:]]
        message = f"{first_error}. Additional errors: {'; '.join(other_errors)}"
        raise type(first_error)(message) from first_error


# Context managers for error collection
class ErrorCollector:
    """Collect errors for batch processing."""

    def __init__(self):
        self.errors: list[Exception] = []
        self.context = ""

    def add_error(self, error: Exception) -> None:
        """Add an error to the collection."""
        self.errors.append(error)

    def set_context(self, context: str) -> None:
        """Set context for error reporting."""
        self.context = context

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def raise_if_errors(self) -> None:
        """Raise collected errors if any exist."""
        if self.errors:
            handle_multiple_errors(self.errors, self.context)

    def __enter__(self) -> "ErrorCollector":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.raise_if_errors()


# Structured error result type
class ErrorResult:
    """Structured error result for better error handling."""

    def __init__(self, error: Exception, context: str = "", recoverable: bool = False):
        self.error = error
        self.context = context
        self.recoverable = recoverable
        self.error_type = type(error).__name__
        self.message = str(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "context": self.context,
            "recoverable": self.recoverable,
            "details": getattr(self.error, "details", {}),
        }
