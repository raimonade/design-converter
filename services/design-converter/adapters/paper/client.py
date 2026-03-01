"""
Paper MCP Client
================
HTTP client for the Paper Design Desktop MCP server.

Paper Desktop exposes a local MCP server on port 29979.
The server uses the standard MCP HTTP+SSE transport:
  - GET  /sse          → Server-Sent Events stream (session handshake)
  - POST /messages     → Send tool-call messages (with mcp-session-id header)
  - POST /mcp          → Simpler direct POST fallback (some versions)

Usage:
    client = PaperClient()
    info   = client.get_basic_info()
    jsx    = client.get_jsx("TO-0")

    # Context manager (auto-connects):
    with PaperClient() as client:
        artboard_id = client.create_artboard("Wallet", {"width": "390px", "height": "844px"})
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PaperConnectionError(Exception):
    """Paper Desktop is not running or MCP server is unreachable."""


class PaperToolError(Exception):
    """A Paper MCP tool call returned an error."""

    def __init__(self, tool: str, message: str) -> None:
        self.tool = tool
        super().__init__(f"Paper tool '{tool}' failed: {message}")


class PaperTimeoutError(Exception):
    """A tool call did not respond within the expected timeout."""


# ---------------------------------------------------------------------------
# Low-level JSON-RPC helpers
# ---------------------------------------------------------------------------

_TIMEOUT_S = 30  # seconds per individual HTTP call
_SSE_POLL_INTERVAL = 0.05  # seconds between SSE line reads
_CALL_TIMEOUT_S = 60  # seconds to wait for a tool result via SSE


def _next_id() -> str:
    return str(uuid.uuid4())


def _make_rpc(method: str, params: Any, rpc_id: str) -> bytes:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": rpc_id}
    return json.dumps(payload).encode()


def _post(
    url: str,
    body: bytes,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = _TIMEOUT_S,
) -> Dict[str, Any]:
    """
    Synchronous HTTP POST.  Returns the parsed JSON body.
    Raises PaperConnectionError on network failure.

    Paper MCP returns SSE format even for direct POST to /mcp:
        event: message
        data: {"result":{...},"jsonrpc":"2.0","id":"..."}

    This function parses both SSE and plain JSON responses.
    """
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return {}
            raw_str = raw.decode("utf-8", errors="replace")
            # Parse SSE format: look for "data: {...}" lines
            # SSE can have multiple data lines - concatenate them
            data_lines = []
            for line in raw_str.split("\n"):
                line = line.rstrip("\r")
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        data_lines.append(data_str)
            if data_lines:
                # Join multiple data lines and parse as single JSON
                combined = "\n".join(data_lines)
                try:
                    return json.loads(combined)
                except json.JSONDecodeError:
                    # Try each line individually (some servers send one JSON per line)
                    for dl in data_lines:
                        try:
                            return json.loads(dl)
                        except json.JSONDecodeError:
                            continue
            # Fall back to plain JSON if no SSE data lines
            raw_str_stripped = raw_str.strip()
            if raw_str_stripped:
                return json.loads(raw_str_stripped)
            return {}
    except URLError as exc:
        raise PaperConnectionError(f"Cannot reach Paper MCP: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise PaperConnectionError(f"Invalid JSON response from Paper MCP: {exc}") from exc
    except Exception as exc:
        raise PaperConnectionError(str(exc)) from exc


# ---------------------------------------------------------------------------
# SSE reader (background thread)
# ---------------------------------------------------------------------------


class _SSESession:
    """
    Opens a persistent SSE connection to Paper's /sse endpoint.
    Collects incoming JSON-RPC *responses* keyed by their `id`.
    A background daemon thread reads the stream; callers poll via `wait_for`.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._session_id: Optional[str] = None
        self._responses: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._error: Optional[Exception] = None

    # ── Connection lifecycle ────────────────────────────────────────────────

    def start(self) -> str:
        """
        Open the SSE stream and wait until the server sends the session ID.
        Returns the session ID string.
        """
        self._thread = threading.Thread(target=self._read_stream, daemon=True)
        self._thread.start()
        if not self._connected.wait(timeout=10):
            if self._error:
                raise self._error
            raise PaperConnectionError(
                "SSE stream did not send a session ID within 10 s"
            )
        return self._session_id  # type: ignore[return-value]

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    # ── Response retrieval ─────────────────────────────────────────────────

    def wait_for(self, rpc_id: str, timeout: float = _CALL_TIMEOUT_S) -> Dict[str, Any]:
        """
        Block until the SSE stream delivers a response for `rpc_id`.
        Returns the full JSON-RPC response dict.
        Raises PaperTimeoutError if nothing arrives in `timeout` seconds.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if rpc_id in self._responses:
                    return self._responses.pop(rpc_id)
            if self._stop.is_set():
                raise PaperConnectionError("SSE stream closed unexpectedly")
            time.sleep(_SSE_POLL_INTERVAL)
        raise PaperTimeoutError(
            f"No response for request '{rpc_id}' after {timeout:.0f}s"
        )

    # ── Background reader ──────────────────────────────────────────────────

    def _read_stream(self) -> None:
        url = f"{self._base_url}/sse"
        req = Request(url)
        req.add_header("Accept", "text/event-stream")
        req.add_header("Cache-Control", "no-cache")
        try:
            with urlopen(req, timeout=None) as resp:
                buffer = ""
                while not self._stop.is_set():
                    chunk = resp.read(1)
                    if not chunk:
                        break
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        self._handle_sse_line(line.rstrip("\r"))
        except Exception as exc:
            if not self._stop.is_set():
                self._error = PaperConnectionError(f"SSE stream error: {exc}")
                self._connected.set()

    def _handle_sse_line(self, line: str) -> None:
        if not line or line.startswith(":"):
            return  # heartbeat / comment

        # Handle event: lines (track current event type)
        if line.startswith("event:"):
            # We could track event type if needed, but for now ignore
            return

        if line.startswith("data:"):
            data_str = line[5:].strip()
            if not data_str:
                return

            # First, try to parse as JSON
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                # Not JSON - might be the plain session-ID handshake line
                # Paper Desktop sends: "data: /messages?sessionId=XXXXX"
                if not self._session_id:
                    # Try to extract sessionId from URL-style data
                    m = re.search(r"sessionId=([^&\s]+)", data_str)
                    if m:
                        self._session_id = m.group(1)
                        self._connected.set()
                    # Also try if data_str IS the session ID directly
                    elif data_str and not data_str.startswith("/"):
                        # Some versions send just the session ID as data
                        self._session_id = data_str
                        self._connected.set()
                return

            # Session handshake from some server versions
            if isinstance(data, dict):
                # Check various session ID field names
                session_id = (
                    data.get("sessionId") or
                    data.get("session_id") or
                    data.get("id") or
                    data.get("session")
                )
                if session_id:
                    self._session_id = str(session_id)
                    self._connected.set()
                    return
                # JSON-RPC response
                rpc_id = data.get("id")
                if rpc_id is not None:
                    with self._lock:
                        self._responses[str(rpc_id)] = data


# ---------------------------------------------------------------------------
# PaperClient
# ---------------------------------------------------------------------------


class PaperClient:
    """
    High-level client for the Paper Design Desktop MCP server.

    By default uses direct POST transport (POST /mcp) which is simpler
    and more reliable than SSE. SSE can be enabled if needed.

    Parameters
    ----------
    host : str
        Hostname of the Paper Desktop HTTP server. Default "127.0.0.1".
    port : int
        Port of the Paper Desktop HTTP server. Default 29979.
    use_sse : bool
        Force SSE (True) or direct POST (False).  Default is False.
        Direct mode is recommended as it's simpler and more reliable.
    """

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 29979

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        use_sse: bool = False,
    ) -> None:
        self._base = f"http://{host}:{port}"
        self._use_sse = use_sse
        self._session: Optional[_SSESession] = None
        self._connected = False

    # ── Context manager ────────────────────────────────────────────────────

    def __enter__(self) -> "PaperClient":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.disconnect()

    # ── Connection lifecycle ────────────────────────────────────────────────

    def connect(self, timeout: float = 10.0) -> None:
        """
        Verify Paper Desktop is running and initialise the preferred transport.

        Parameters
        ----------
        timeout : float
            Connection timeout in seconds. Default 10.0.

        Raises
        ------
        PaperConnectionError
            If Paper Desktop is not reachable within the timeout.
        """
        if self._connected:
            return

        if not self._use_sse:
            self._ping_direct(timeout=timeout)
            self._connected = True
            return

        # SSE mode - try SSE first; fall back to direct POST on failure
        try:
            self._session = _SSESession(self._base)
            session_id = self._session.start()
            # Verify we actually got a valid session ID
            if not session_id:
                raise PaperConnectionError("SSE did not provide a valid session ID")
            self._connected = True
        except Exception as e:
            # SSE failed — try direct POST transport
            self._session = None
            try:
                self._ping_direct(timeout=timeout)
                self._use_sse = False
                self._connected = True
            except PaperConnectionError:
                raise PaperConnectionError(
                    f"Paper Desktop MCP server not reachable at {self._base}. "
                    "Is Paper Desktop running? (SSE error: {e})"
                )

    def disconnect(self) -> None:
        if self._session:
            self._session.stop()
            self._session = None
        self._connected = False

    def is_connected(self) -> bool:
        """Quick liveness check (does not raise)."""
        if not self._connected:
            return False
        try:
            self._ping_direct(timeout=5.0)
            return True
        except Exception:
            return False

    # ── Core RPC ───────────────────────────────────────────────────────────

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a Paper MCP tool and return the result payload.

        The result is the `content` list from the MCP tools/call response.
        Each item is typically {"type": "text", "text": "<json or string>"}.
        Returns the parsed first text item if it looks like JSON,
        otherwise returns the raw content list.

        Raises
        ------
        PaperToolError      if the tool returns an error.
        PaperConnectionError if the server is not reachable.
        PaperTimeoutError   if the call times out.
        """
        rpc_id = _next_id()
        body = _make_rpc(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            rpc_id,
        )

        if not self._connected:
            self.connect()

        if self._use_sse:
            response = self._call_via_sse(rpc_id, body)
        else:
            response = self._call_direct(body)

        return self._unwrap(tool_name, response)

    # ── Transport implementations ──────────────────────────────────────────

    def _call_via_sse(self, rpc_id: str, body: bytes) -> Dict[str, Any]:
        """POST to /messages and await response on the SSE stream."""
        assert self._session is not None
        session_id = self._session._session_id
        if not session_id:
            raise PaperConnectionError("SSE session ID not available")
        url = f"{self._base}/messages"
        headers = {"mcp-session-id": session_id}
        try:
            _post(url, body, headers=headers)
        except PaperConnectionError as exc:
            raise exc
        return self._session.wait_for(rpc_id)

    def _call_direct(self, body: bytes, timeout: float = _TIMEOUT_S) -> Dict[str, Any]:
        """POST directly to /mcp (simple synchronous transport)."""
        url = f"{self._base}/mcp"
        return _post(url, body, timeout=timeout)

    def _ping_direct(self, timeout: float = _TIMEOUT_S) -> None:
        """Lightweight ping to verify the server is alive."""
        body = _make_rpc("tools/list", {}, _next_id())
        try:
            resp = _post(f"{self._base}/mcp", body, timeout=timeout)
            # Accept any non-error response
            if "error" in resp and resp["error"].get("code", 0) not in (-32601,):
                raise PaperConnectionError(str(resp["error"]))
        except PaperConnectionError:
            raise
        except Exception as exc:
            raise PaperConnectionError(str(exc)) from exc

    # ── Response unwrapping ────────────────────────────────────────────────

    @staticmethod
    def _unwrap(tool_name: str, response: Dict[str, Any]) -> Any:
        """
        Extract the useful payload from a JSON-RPC response.

        MCP tools/call response shape:
          {"jsonrpc":"2.0","id":"...","result":{"content":[{"type":"text","text":"..."}]}}
        """
        if "error" in response:
            err = response["error"]
            raise PaperToolError(tool_name, str(err.get("message", err)))

        result = response.get("result", response)

        # Unwrap MCP content array
        content = result.get("content") if isinstance(result, dict) else None
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and first.get("type") == "text":
                text = first["text"]
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    return text

        return result

    # ── Paper tool wrappers ────────────────────────────────────────────────

    def get_basic_info(self) -> Dict[str, Any]:
        """
        Return basic information about the currently open Paper file.

        Example response::
            {
              "fileName": "Wallet2",
              "nodeCount": 1929,
              "artboards": [
                {"id": "TO-0", "name": "Wallet Original", "width": 390, "height": 844}
              ]
            }
        """
        return self.call_tool("get_basic_info", {})

    def list_artboards(self) -> List[Dict[str, Any]]:
        """
        Return a list of top-level artboard nodes.
        Each item: {"id": str, "name": str, "width": int, "height": int}
        """
        info = self.get_basic_info()
        if isinstance(info, dict):
            return info.get("artboards", info.get("frames", []))
        return []

    def get_jsx(
        self,
        node_id: str,
        mode: str = "inline-styles",
    ) -> str:
        """
        Export a node as JSX.

        Parameters
        ----------
        node_id : str
            Paper node / artboard ID (e.g. "TO-0").
        mode : str
            "inline-styles" (default) or "tailwind".

        Returns
        -------
        str  — JSX string representing the node tree.
        """
        result = self.call_tool("get_jsx", {"nodeId": node_id, "mode": mode})
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("jsx", result.get("code", str(result)))
        return str(result)

    def get_node(self, node_id: str) -> Dict[str, Any]:
        """
        Return raw node data for a single node by ID.
        Shape depends on Paper version; usually includes x, y, width, height, type.
        """
        return self.call_tool("get_node", {"nodeId": node_id})

    def get_nodes_by_selector(
        self,
        selector: str,
        root_node_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return a list of nodes matching a CSS-like selector.

        Parameters
        ----------
        selector : str
            e.g. "#my-id", ".my-class", "Frame", "*"
        root_node_id : str | None
            Scope the search to a subtree.  None = entire document.
        """
        args: Dict[str, Any] = {"selector": selector}
        if root_node_id:
            args["rootNodeId"] = root_node_id
        result = self.call_tool("get_nodes_by_selector", args)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("nodes", [])
        return []

    def create_artboard(
        self,
        name: str,
        styles: Dict[str, Any],
        x: int = 0,
        y: int = 0,
    ) -> str:
        """
        Create a new artboard in the current Paper file.

        Parameters
        ----------
        name   : str  — Display name of the artboard.
        styles : dict — CSS-style dict, e.g. {"width": "390px", "height": "844px",
                                                "backgroundColor": "#050508"}.
        x, y   : int  — Canvas position (default 0, 0).

        Returns
        -------
        str — ID of the newly created artboard.
        """
        result = self.call_tool(
            "create_artboard",
            {"name": name, "styles": styles, "x": x, "y": y},
        )
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("id", result.get("nodeId", ""))
        return str(result)

    def write_html(
        self,
        target_node_id: str,
        html: str,
        mode: str = "replace",
    ) -> Dict[str, Any]:
        """
        Convert an HTML string to Paper design nodes inside `target_node_id`.

        Parameters
        ----------
        target_node_id : str  — ID of the parent container to write into.
        html           : str  — HTML markup with inline styles.
        mode           : str  — "replace" (clear + insert) or "append".

        Returns
        -------
        dict with at minimum {"success": bool, "nodeCount": int}.
        """
        result = self.call_tool(
            "write_html",
            {"targetNodeId": target_node_id, "html": html, "mode": mode},
        )
        if isinstance(result, dict):
            return result
        return {"success": bool(result), "raw": result}

    def rename_nodes(
        self,
        updates: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Batch-rename nodes.

        Parameters
        ----------
        updates : list of {"nodeId": str, "name": str}

        Returns
        -------
        dict — operation result.
        """
        return self.call_tool("rename_nodes", {"updates": updates})

    def delete_nodes(self, node_ids: List[str]) -> Dict[str, Any]:
        """Delete one or more nodes by ID."""
        return self.call_tool("delete_nodes", {"nodeIds": node_ids})

    def set_styles(
        self,
        node_id: str,
        styles: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply CSS-style properties to an existing node."""
        return self.call_tool("set_styles", {"nodeId": node_id, "styles": styles})

    def move_node(
        self,
        node_id: str,
        new_parent_id: str,
        index: int = -1,
    ) -> Dict[str, Any]:
        """Move a node to a different parent container."""
        return self.call_tool(
            "move_node",
            {"nodeId": node_id, "newParentId": new_parent_id, "index": index},
        )

    def screenshot(
        self,
        node_id: str,
        scale: float = 1.0,
        format: str = "png",
    ) -> Optional[bytes]:
        """
        Capture a screenshot of the given node.

        Returns raw PNG bytes, or None if the tool is not available.
        """
        try:
            result = self.call_tool(
                "screenshot",
                {"nodeId": node_id, "scale": scale, "format": format},
            )
            if isinstance(result, dict) and "data" in result:
                import base64

                return base64.b64decode(result["data"])
            return None
        except PaperToolError:
            return None

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Return the list of tools advertised by this Paper MCP server.
        Useful for capability detection.
        """
        if not self._connected:
            self.connect()
        rpc_id = _next_id()
        body = _make_rpc("tools/list", {}, rpc_id)
        if self._use_sse:
            resp = self._call_via_sse(rpc_id, body)
        else:
            resp = self._call_direct(body)
        result = resp.get("result", {})
        return result.get("tools", [])

    def has_tool(self, tool_name: str) -> bool:
        """Return True if the Paper MCP server advertises the named tool."""
        try:
            tools = self.list_tools()
            return any(t.get("name") == tool_name for t in tools)
        except Exception:
            return False

    # ── Convenience helpers ────────────────────────────────────────────────

    def get_artboard_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find an artboard by its display name (case-insensitive)."""
        for ab in self.list_artboards():
            if ab.get("name", "").lower() == name.lower():
                return ab
        return None

    def get_or_create_artboard(
        self,
        name: str,
        width: int = 390,
        height: int = 844,
        background: str = "#050508",
        x: int = 0,
        y: int = 0,
    ) -> str:
        """
        Return the ID of an existing artboard named `name`, or create one.
        """
        existing = self.get_artboard_by_name(name)
        if existing:
            return existing["id"]
        return self.create_artboard(
            name,
            {
                "width": f"{width}px",
                "height": f"{height}px",
                "backgroundColor": background,
            },
            x=x,
            y=y,
        )

    # ── Diagnostics ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        transport = "SSE" if self._use_sse else "direct"
        status = "connected" if self._connected else "disconnected"
        return f"<PaperClient base={self._base!r} transport={transport} status={status}>"
