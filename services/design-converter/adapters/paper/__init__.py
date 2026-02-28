"""
Paper Design Adapter
====================
Read from and write to Paper Design Desktop via its local MCP server.

Public surface
--------------
    PaperClient  — low-level MCP HTTP client (port 29979)
    PaperReader  — Paper → UNT (reads via get_jsx / get_node)
    PaperWriter  — UNT → Paper (writes via write_html)
"""

from .client import PaperClient, PaperConnectionError, PaperTimeoutError, PaperToolError
from .reader import PaperReader
from .writer import PaperWriter

__all__ = [
    "PaperClient",
    "PaperConnectionError",
    "PaperTimeoutError",
    "PaperToolError",
    "PaperReader",
    "PaperWriter",
]
