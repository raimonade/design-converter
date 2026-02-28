"""
Figma Adapter
=============
Reads from and writes to Figma via the REST API.

Public surface
--------------
    from adapters.figma import FigmaClient, FigmaReader, FigmaWriter
"""

from .client import (
    FigmaAPIError,
    FigmaAuthError,
    FigmaClient,
    FigmaNotFoundError,
    FigmaRateLimitError,
)
from .reader import FigmaReader
from .writer import FigmaWriter

__all__ = [
    "FigmaClient",
    "FigmaReader",
    "FigmaWriter",
    # Exceptions
    "FigmaAuthError",
    "FigmaAPIError",
    "FigmaNotFoundError",
    "FigmaRateLimitError",
]
