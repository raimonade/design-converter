"""
Base Adapter Interfaces
=======================
Every tool adapter (Paper, Pencil, Figma) implements these two classes.

Architecture
------------
Reader  →  reads from a design tool  →  returns UNNode tree
Writer  →  receives UNNode tree      →  writes to a design tool

Both classes are intentionally thin — they define the contract only.
All HTTP/subprocess I/O lives in the concrete adapter, not here.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ir.nodes import UNNode

# ---------------------------------------------------------------------------
# Base Reader
# ---------------------------------------------------------------------------


class BaseReader(ABC):
    """
    Read from a design tool and return a UNNode tree.

    Lifecycle
    ---------
    1. __init__()  — configure credentials / endpoints
    2. connect()   — open session / start subprocess (if needed)
    3. read_node() — extract one node tree as UNNode
    4. disconnect()— clean up

    Readers are also usable as context managers:
        with PaperReader() as reader:
            tree = reader.read_node("TO-0")
    """

    tool_name: str = "base"  # Override in subclass: "paper" | "pencil" | "figma"

    def connect(self) -> None:
        """Open connection to the tool (HTTP session, subprocess, API auth…)."""
        pass

    def disconnect(self) -> None:
        """Close connection and release resources."""
        pass

    def __enter__(self) -> "BaseReader":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.disconnect()

    # ── Required ───────────────────────────────────────────────────────────

    @abstractmethod
    def read_node(self, node_id: str) -> UNNode:
        """
        Read the node identified by `node_id` from the design tool,
        including its full descendant tree, and return it as a UNNode.

        Raises
        ------
        NodeNotFoundError  if the node doesn't exist.
        ConnectionError    if the tool is unreachable.
        """
        ...

    # ── Optional helpers ───────────────────────────────────────────────────

    def list_nodes(self) -> List[Dict[str, Any]]:
        """
        Return a flat list of top-level nodes in the currently open file.
        Each item is a dict with at least {"id": str, "name": str, "type": str}.
        Default implementation returns an empty list.
        """
        return []

    def get_file_info(self) -> Dict[str, Any]:
        """
        Return metadata about the current file.
        e.g. {"fileName": "Wallet2", "nodeCount": 720, "artboardCount": 4}
        Default implementation returns an empty dict.
        """
        return {}

    def screenshot(self, node_id: str, scale: float = 1.0) -> Optional[bytes]:
        """
        Return a PNG screenshot of the node as bytes, or None if unsupported.
        """
        return None


# ---------------------------------------------------------------------------
# Base Writer
# ---------------------------------------------------------------------------


class BaseWriter(ABC):
    """
    Write a UNNode tree to a design tool.

    Lifecycle
    ---------
    1. __init__()     — configure credentials / endpoints
    2. connect()      — open session / start subprocess (if needed)
    3. write_node()   — create or replace a node from a UNNode tree
    4. disconnect()   — clean up

    Writers are also usable as context managers:
        with PencilWriter() as writer:
            writer.write_node(tree, parent_id="root")
    """

    tool_name: str = "base"

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def __enter__(self) -> "BaseWriter":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.disconnect()

    # ── Required ───────────────────────────────────────────────────────────

    @abstractmethod
    def write_node(
        self,
        node: UNNode,
        parent_id: str = "",
        replace_id: str = "",
    ) -> str:
        """
        Write `node` (and its children) into the design tool.

        Parameters
        ----------
        node        : The UNNode tree to create.
        parent_id   : ID of the parent container to insert into.
                      Empty string means "top level / current page".
        replace_id  : If set, replace the existing node with this ID
                      instead of inserting a new one.

        Returns
        -------
        The new node's ID in the target tool (str).

        Raises
        ------
        ConnectionError  if the tool is unreachable.
        WriteError       if the tool rejects the node data.
        """
        ...

    # ── Optional helpers ───────────────────────────────────────────────────

    def delete_node(self, node_id: str) -> None:
        """Delete a node by ID. No-op by default."""
        pass

    def move_node(self, node_id: str, new_parent_id: str, index: int = -1) -> None:
        """Move a node to a different parent. No-op by default."""
        pass

    def screenshot(self, node_id: str, scale: float = 1.0) -> Optional[bytes]:
        """Return a PNG screenshot of a written node, or None."""
        return None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NodeNotFoundError(Exception):
    """Raised when a requested node ID does not exist in the tool."""

    def __init__(self, node_id: str, tool: str = ""):
        self.node_id = node_id
        self.tool = tool
        msg = f"Node '{node_id}' not found"
        if tool:
            msg += f" in {tool}"
        super().__init__(msg)


class ConnectionError(Exception):
    """Raised when the adapter cannot connect to the design tool."""

    def __init__(self, tool: str, reason: str = ""):
        self.tool = tool
        self.reason = reason
        msg = f"Cannot connect to {tool}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class WriteError(Exception):
    """Raised when the tool rejects a write operation."""

    def __init__(self, tool: str, reason: str = ""):
        self.tool = tool
        self.reason = reason
        msg = f"Write failed in {tool}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Registry  (optional — lets converter.py look up adapters by name)
# ---------------------------------------------------------------------------

_READERS: Dict[str, type] = {}
_WRITERS: Dict[str, type] = {}


def register_reader(tool_name: str, cls: type) -> None:
    _READERS[tool_name] = cls


def register_writer(tool_name: str, cls: type) -> None:
    _WRITERS[tool_name] = cls


def get_reader(tool_name: str) -> type:
    if tool_name not in _READERS:
        raise ValueError(
            f"No reader registered for '{tool_name}'. "
            f"Available: {list(_READERS.keys())}"
        )
    return _READERS[tool_name]


def get_writer(tool_name: str) -> type:
    if tool_name not in _WRITERS:
        raise ValueError(
            f"No writer registered for '{tool_name}'. "
            f"Available: {list(_WRITERS.keys())}"
        )
    return _WRITERS[tool_name]
