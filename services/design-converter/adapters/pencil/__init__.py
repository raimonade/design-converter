"""
Pencil Adapter
==============
Read from and write to Pencil.dev via its local MCP server.

Public API
----------
    from adapters.pencil import PencilReader, PencilWriter, PencilClient
"""

from .client import (
    PencilClient,
    PencilConnectionError,
    PencilToolError,
    find_pencil_port,
)
from .reader import PencilReader
from .writer import PencilWriter

__all__ = [
    "PencilClient",
    "PencilConnectionError",
    "PencilToolError",
    "PencilReader",
    "PencilWriter",
    "find_pencil_port",
]
