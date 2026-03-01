"""
Figma Adapter
=============
Reads from and writes to Figma via the REST API.

Public surface
--------------
    from adapters.figma import FigmaClient, FigmaReader, FigmaWriter

HTTP Bridge (for live execution):
    from adapters.figma import FigmaBridgeClient, FigmaBridgeServer
    client = FigmaBridgeClient(port=9223)
    if client.is_connected():
        result = client.execute_code("figma.notify('Hello!')")
"""

from .client import (
    FigmaAPIError,
    FigmaAuthError,
    FigmaClient,
    FigmaNotFoundError,
    FigmaRateLimitError,
)
from .http_bridge import BridgeResult, FigmaBridgeClient
from .reader import FigmaReader
from .writer import FigmaWriter

__all__ = [
    "FigmaClient",
    "FigmaReader",
    "FigmaWriter",
    # HTTP Bridge
    "FigmaBridgeClient",
    "BridgeResult",
    # Exceptions
    "FigmaAuthError",
    "FigmaAPIError",
    "FigmaNotFoundError",
    "FigmaRateLimitError",
]
