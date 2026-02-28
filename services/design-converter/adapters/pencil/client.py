"""
Pencil MCP Client
=================
HTTP client for the Pencil.dev MCP server.

Pencil runs a local MCP server (mcp-server-darwin-arm64) that exposes design
tools via JSON-RPC over HTTP.  The default port is 19002 but it can vary —
this client auto-detects the live port by inspecting running processes and
by probing known candidate ports.

Usage
-----
    from adapters.pencil.client import PencilClient

    with PencilClient() as client:
        info   = client.get_file_info()
        boards = client.list_artboards()
        node   = client.get_node("frame-id")
        new_id = client.create_frame(parent_id="", name="Mirror", x=0, y=0,
                                     width=390, height=844)

Protocol
--------
Pencil's MCP server speaks JSON-RPC 2.0 over HTTP POST.
The client also supports the Anthropic MCP HTTP+SSE transport
(GET /sse  +  POST /messages?sessionId=<id>) as a fallback.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Ports to probe when auto-detecting Pencil's MCP server.
_CANDIDATE_PORTS: Tuple[int, ...] = (19002, 19003, 19000, 19001, 19004, 19005)

# How long (seconds) to wait for a single HTTP request before giving up.
_HTTP_TIMEOUT: float = 15.0

# How long (seconds) to wait when probing a port.
_PROBE_TIMEOUT: float = 2.0

# JSON-RPC version string.
_JSONRPC = "2.0"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PencilConnectionError(Exception):
    """Raised when the client cannot reach the Pencil MCP server."""


class PencilToolError(Exception):
    """Raised when a tool call returns an MCP error response."""

    def __init__(self, tool: str, code: int, message: str) -> None:
        self.tool = tool
        self.code = code
        self.message = message
        super().__init__(f"[{tool}] MCP error {code}: {message}")


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------


def _http_post(
    url: str, payload: Dict[str, Any], timeout: float = _HTTP_TIMEOUT
) -> Dict[str, Any]:
    """
    Send a JSON POST request and return the parsed response body.

    Raises
    ------
    PencilConnectionError  on network-level failure.
    PencilToolError        on a JSON-RPC error response.
    """
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise PencilConnectionError(f"HTTP POST to {url} failed: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PencilConnectionError(
            f"Non-JSON response from {url}: {raw[:200]}"
        ) from exc

    if "error" in data:
        err = data["error"]
        raise PencilToolError(
            tool=payload.get("method", "unknown"),
            code=err.get("code", -1),
            message=err.get("message", str(err)),
        )

    return data


def _http_get(url: str, timeout: float = _HTTP_TIMEOUT) -> str:
    """Perform a simple GET and return the response body as a string."""
    req = urllib.request.Request(
        url, headers={"Accept": "application/json, text/event-stream"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise PencilConnectionError(f"HTTP GET to {url} failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Port detection
# ---------------------------------------------------------------------------


def _detect_port_from_processes() -> Optional[int]:
    """
    Inspect running processes for Pencil's mcp-server and extract the port
    from its command-line arguments.

    Works on macOS/Linux via `ps aux` or `lsof`.
    """
    # Strategy 1: look for --port flag in the mcp-server process args
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "mcp-server" in line and "pencil" in line.lower():
                m = re.search(r"--port[=\s]+(\d+)", line)
                if m:
                    return int(m.group(1))
                # Some servers just list the port as a bare arg after the binary
                m = re.search(r"mcp-server[^\s]*\s+(\d{4,5})", line)
                if m:
                    return int(m.group(1))
    except (subprocess.SubprocessError, OSError):
        pass

    # Strategy 2: lsof — find ports that a process named mcp-server is listening on
    try:
        result = subprocess.run(
            ["lsof", "-i", "TCP", "-sTCP:LISTEN", "-n", "-P"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "mcp-server" in line.lower() or "pencil" in line.lower():
                m = re.search(r":(\d{4,5})\s+\(LISTEN\)", line)
                if m:
                    return int(m.group(1))
    except (subprocess.SubprocessError, OSError):
        pass

    return None


def _probe_port(host: str, port: int) -> bool:
    """Return True if a Pencil MCP server is listening on host:port."""
    url = f"http://{host}:{port}/mcp"
    try:
        _http_get(url, timeout=_PROBE_TIMEOUT)
        return True
    except PencilConnectionError:
        pass

    # Also try the /health or / endpoint
    for path in ("/health", "/", "/sse"):
        try:
            url2 = f"http://{host}:{port}{path}"
            _http_get(url2, timeout=_PROBE_TIMEOUT)
            return True
        except PencilConnectionError:
            pass

    return False


def find_pencil_port(host: str = "127.0.0.1") -> int:
    """
    Return the port where Pencil's MCP server is listening.

    Search order:
    1. Parse running process arguments.
    2. Probe known candidate ports.

    Raises PencilConnectionError if no server is found.
    """
    # Try process inspection first (cheapest)
    detected = _detect_port_from_processes()
    if detected and _probe_port(host, detected):
        log.debug("Pencil MCP found via process inspection on port %d", detected)
        return detected

    # Probe known ports
    for port in _CANDIDATE_PORTS:
        if _probe_port(host, port):
            log.debug("Pencil MCP found by port probe on port %d", port)
            return port

    raise PencilConnectionError(
        f"Pencil MCP server not found on {host}. "
        f"Tried ports: {list(_CANDIDATE_PORTS)}. "
        "Make sure Pencil.dev is running with its MCP server enabled."
    )


# ---------------------------------------------------------------------------
# MCP session management (SSE transport)
# ---------------------------------------------------------------------------


class _SSESession:
    """
    Manages a session with an MCP server that uses the HTTP+SSE transport.

    The SSE transport:
      1. Client GETs /sse — server sends an 'endpoint' event with a session URL.
      2. Client POSTs JSON-RPC messages to that session URL.
      3. Server sends responses as SSE 'message' events on the /sse stream.

    Because we can't block reading an SSE stream in a simple synchronous client,
    we use a simplified request-response approach:
      - POST to /messages?sessionId=<id>
      - Read the SSE stream briefly for the matching response.
    This works for short tool calls (< HTTP_TIMEOUT seconds).
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None
        self.endpoint: Optional[str] = None

    def open(self) -> None:
        """Establish SSE session and extract the session endpoint."""
        sse_url = f"{self.base_url}/sse"
        req = urllib.request.Request(
            sse_url,
            headers={"Accept": "text/event-stream"},
        )
        try:
            # Read enough bytes to capture the 'endpoint' event
            with urllib.request.urlopen(req, timeout=_PROBE_TIMEOUT + 1) as resp:
                chunk = resp.read(4096).decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise PencilConnectionError(
                f"Cannot open SSE stream at {sse_url}: {exc}"
            ) from exc

        # Parse SSE events: look for "event: endpoint\ndata: <url>"
        m = re.search(r"event:\s*endpoint\s*\ndata:\s*(\S+)", chunk)
        if m:
            endpoint_path = m.group(1)
            self.endpoint = (
                endpoint_path
                if endpoint_path.startswith("http")
                else f"{self.base_url}{endpoint_path}"
            )
            # Extract session id from endpoint URL
            sid = re.search(r"sessionId=([^&\s]+)", endpoint_path)
            if sid:
                self.session_id = sid.group(1)
            log.debug(
                "SSE session endpoint: %s (id=%s)", self.endpoint, self.session_id
            )
        else:
            raise PencilConnectionError(
                f"Could not find 'endpoint' event in SSE stream from {sse_url}. "
                f"Raw: {chunk[:200]}"
            )


# ---------------------------------------------------------------------------
# Main Client
# ---------------------------------------------------------------------------


class PencilClient:
    """
    Synchronous MCP client for Pencil.dev.

    Supports two transport modes:
      - 'post'  : Direct JSON-RPC POST to /mcp  (simpler, preferred)
      - 'sse'   : HTTP+SSE transport via /sse + /messages

    The mode is auto-detected on connect().

    Parameters
    ----------
    host        : MCP server host (default '127.0.0.1')
    port        : MCP server port.  Pass None to auto-detect.
    timeout     : HTTP request timeout in seconds.
    auto_detect : Whether to auto-detect port when port=None (default True).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        timeout: float = _HTTP_TIMEOUT,
        auto_detect: bool = True,
    ) -> None:
        self.host = host
        self._requested_port = port
        self.port: int = port or 0
        self.timeout = timeout
        self.auto_detect = auto_detect

        self._transport: str = "post"  # 'post' | 'sse'
        self._sse_session: Optional[_SSESession] = None
        self._rpc_id: int = 0
        self._connected: bool = False

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Detect port (if needed) and negotiate transport."""
        if self._connected:
            return

        if not self.port:
            if self.auto_detect:
                self.port = find_pencil_port(self.host)
            else:
                self.port = _CANDIDATE_PORTS[0]

        base = f"http://{self.host}:{self.port}"

        # Try simple POST transport first
        try:
            _http_get(f"{base}/mcp", timeout=_PROBE_TIMEOUT)
            self._transport = "post"
            log.info("Pencil MCP connected via POST transport at %s", base)
        except PencilConnectionError:
            # Fall back to SSE transport
            try:
                sess = _SSESession(base)
                sess.open()
                self._sse_session = sess
                self._transport = "sse"
                log.info("Pencil MCP connected via SSE transport at %s", base)
            except PencilConnectionError as exc:
                raise PencilConnectionError(
                    f"Cannot connect to Pencil MCP at {base}: {exc}"
                ) from exc

        self._connected = True

    def disconnect(self) -> None:
        self._connected = False
        self._sse_session = None

    def __enter__(self) -> "PencilClient":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.disconnect()

    # ── JSON-RPC core ──────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _rpc(self, method: str, params: Dict[str, Any]) -> Any:
        """Send a JSON-RPC request and return the 'result' field."""
        payload = {
            "jsonrpc": _JSONRPC,
            "id": self._next_id(),
            "method": method,
            "params": params,
        }

        if self._transport == "post":
            url = f"http://{self.host}:{self.port}/mcp"
            data = _http_post(url, payload, timeout=self.timeout)
            return data.get("result")

        # SSE transport
        if self._sse_session is None or self._sse_session.endpoint is None:
            raise PencilConnectionError(
                "SSE session not established. Call connect() first."
            )
        data = _http_post(self._sse_session.endpoint, payload, timeout=self.timeout)
        return data.get("result")

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool by name.

        Returns the tool result (parsed from the 'result' field).
        Raises PencilToolError on MCP-level errors.
        """
        if not self._connected:
            self.connect()

        result = self._rpc("tools/call", {"name": name, "arguments": arguments})

        # MCP tools/call returns: {"content": [...], "isError": bool}
        if isinstance(result, dict):
            if result.get("isError"):
                content = result.get("content", [])
                msg = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict)
                ) or str(content)
                raise PencilToolError(name, -1, msg)
            # Extract text content
            content = result.get("content", [])
            if content and isinstance(content, list):
                texts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                if texts:
                    combined = "\n".join(texts)
                    # Try to parse as JSON
                    try:
                        return json.loads(combined)
                    except json.JSONDecodeError:
                        return combined
            return result

        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return the list of tools available on this MCP server."""
        if not self._connected:
            self.connect()
        result = self._rpc("tools/list", {})
        if isinstance(result, dict):
            return result.get("tools", [])
        return []

    # ── File-level tools ───────────────────────────────────────────────────

    def get_file_info(self) -> Dict[str, Any]:
        """
        Return metadata about the currently open Pencil file.

        Returns a dict with keys like:
          fileName, filePath, pageCount, artboardCount, nodeCount
        """
        try:
            return self.call_tool("get_file_info", {}) or {}
        except PencilToolError:
            # Fall back to get_basic_info if the tool name differs
            try:
                return self.call_tool("get_basic_info", {}) or {}
            except PencilToolError:
                return {}

    def list_artboards(self) -> List[Dict[str, Any]]:
        """
        Return a list of artboards (top-level frames) in the current file.

        Each item has: {id, name, x, y, width, height}
        """
        try:
            result = self.call_tool("list_artboards", {})
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("artboards", result.get("frames", []))
        except PencilToolError:
            pass

        # Fall back to list_frames
        try:
            result = self.call_tool("list_frames", {})
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("frames", [])
        except PencilToolError:
            pass

        return []

    def get_node(self, node_id: str, depth: int = -1) -> Dict[str, Any]:
        """
        Return the full node tree rooted at `node_id`.

        Parameters
        ----------
        node_id : The node's ID string.
        depth   : How many levels of children to include.  -1 means unlimited.
        """
        args: Dict[str, Any] = {"nodeId": node_id}
        if depth >= 0:
            args["depth"] = depth

        try:
            result = self.call_tool("get_node", args)
            if isinstance(result, dict):
                return result
        except PencilToolError:
            pass

        # Alternative tool name
        try:
            result = self.call_tool("get_node_tree", args)
            if isinstance(result, dict):
                return result
        except PencilToolError:
            pass

        return {}

    def get_page(self, page_id: str = "") -> Dict[str, Any]:
        """Return the full page node tree."""
        args: Dict[str, Any] = {}
        if page_id:
            args["pageId"] = page_id
        try:
            return self.call_tool("get_page", args) or {}
        except PencilToolError:
            return {}

    # ── Read helpers ───────────────────────────────────────────────────────

    def get_nodes_by_type(
        self, node_type: str, root_id: str = ""
    ) -> List[Dict[str, Any]]:
        """Return all nodes of a given type within the tree."""
        args: Dict[str, Any] = {"type": node_type}
        if root_id:
            args["rootId"] = root_id
        try:
            result = self.call_tool("get_nodes_by_type", args)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("nodes", [])
        except PencilToolError:
            pass
        return []

    def get_styles(self) -> Dict[str, Any]:
        """Return the design token / style library of the current file."""
        try:
            return self.call_tool("get_styles", {}) or {}
        except PencilToolError:
            return {}

    def export_node(
        self,
        node_id: str,
        format: str = "png",
        scale: float = 1.0,
    ) -> Optional[bytes]:
        """
        Export a node as an image.

        Returns raw bytes (PNG/SVG) or None if unsupported.
        """
        try:
            result = self.call_tool(
                "export_node",
                {"nodeId": node_id, "format": format, "scale": scale},
            )
            if isinstance(result, (bytes, bytearray)):
                return bytes(result)
            if isinstance(result, str):
                import base64

                try:
                    return base64.b64decode(result)
                except Exception:
                    return result.encode("utf-8")
        except PencilToolError:
            pass
        return None

    # ── Write tools — Frame / Artboard ─────────────────────────────────────

    def create_artboard(
        self,
        name: str,
        x: float = 0.0,
        y: float = 0.0,
        width: float = 390.0,
        height: float = 844.0,
        *,
        background_color: str = "#FFFFFF",
    ) -> str:
        """
        Create a new top-level artboard and return its node ID.
        """
        result = self.call_tool(
            "create_artboard",
            {
                "name": name,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "backgroundColor": background_color,
            },
        )
        return _extract_id(result)

    def create_frame(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        parent_id: str = "",
        background_color: Optional[str] = None,
        corner_radius: float = 0.0,
        clip_content: bool = False,
        layout: str = "none",
        layout_direction: str = "vertical",
        padding: Optional[List[float]] = None,
        gap: float = 0.0,
        align_items: str = "start",
        justify_content: str = "start",
        opacity: float = 1.0,
        visible: bool = True,
    ) -> str:
        """
        Create a frame node and return its ID.

        Parameters
        ----------
        layout : 'none' | 'flex'
        layout_direction : 'horizontal' | 'vertical' (only with layout='flex')
        padding : [top, right, bottom, left] in pixels
        """
        args: Dict[str, Any] = {
            "name": name,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "cornerRadius": corner_radius,
            "clipContent": clip_content,
            "opacity": opacity,
            "visible": visible,
        }
        if parent_id:
            args["parentId"] = parent_id
        if background_color:
            args["backgroundColor"] = background_color
        if layout != "none":
            args["layout"] = layout
            args["layoutDirection"] = layout_direction
            args["gap"] = gap
            args["alignItems"] = align_items
            args["justifyContent"] = justify_content
        if padding:
            args["padding"] = padding

        result = self.call_tool("create_frame", args)
        return _extract_id(result)

    # ── Write tools — Shapes ───────────────────────────────────────────────

    def create_rectangle(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        parent_id: str = "",
        fill_color: Optional[str] = None,
        corner_radius: float = 0.0,
        stroke_color: Optional[str] = None,
        stroke_width: float = 1.0,
        opacity: float = 1.0,
    ) -> str:
        """Create a rectangle and return its ID."""
        args: Dict[str, Any] = {
            "name": name,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "cornerRadius": corner_radius,
            "opacity": opacity,
        }
        if parent_id:
            args["parentId"] = parent_id
        if fill_color:
            args["fillColor"] = fill_color
        if stroke_color:
            args["strokeColor"] = stroke_color
            args["strokeWidth"] = stroke_width

        result = self.call_tool("create_rectangle", args)
        return _extract_id(result)

    def create_ellipse(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        parent_id: str = "",
        fill_color: Optional[str] = None,
        stroke_color: Optional[str] = None,
        stroke_width: float = 1.0,
        opacity: float = 1.0,
    ) -> str:
        """Create an ellipse and return its ID."""
        args: Dict[str, Any] = {
            "name": name,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "opacity": opacity,
        }
        if parent_id:
            args["parentId"] = parent_id
        if fill_color:
            args["fillColor"] = fill_color
        if stroke_color:
            args["strokeColor"] = stroke_color
            args["strokeWidth"] = stroke_width

        result = self.call_tool("create_ellipse", args)
        return _extract_id(result)

    def create_path(
        self,
        name: str,
        path_data: str,
        *,
        parent_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
        width: Optional[float] = None,
        height: Optional[float] = None,
        fill_color: Optional[str] = None,
        stroke_color: Optional[str] = None,
        stroke_width: float = 1.0,
        fill_rule: str = "nonzero",
        opacity: float = 1.0,
    ) -> str:
        """Create a vector path node and return its ID."""
        args: Dict[str, Any] = {
            "name": name,
            "pathData": path_data,
            "x": x,
            "y": y,
            "fillRule": fill_rule,
            "opacity": opacity,
        }
        if parent_id:
            args["parentId"] = parent_id
        if width is not None:
            args["width"] = width
        if height is not None:
            args["height"] = height
        if fill_color:
            args["fillColor"] = fill_color
        if stroke_color:
            args["strokeColor"] = stroke_color
            args["strokeWidth"] = stroke_width

        result = self.call_tool("create_path", args)
        return _extract_id(result)

    # ── Write tools — Text ─────────────────────────────────────────────────

    def create_text(
        self,
        name: str,
        content: str,
        x: float,
        y: float,
        *,
        parent_id: str = "",
        font_family: str = "Inter",
        font_size: float = 14.0,
        font_weight: str = "400",
        font_style: str = "normal",
        color: str = "#000000",
        text_align: str = "left",
        line_height: Optional[float] = None,
        letter_spacing: float = 0.0,
        text_transform: str = "none",
        text_decoration: str = "none",
        width: Optional[float] = None,
        height: Optional[float] = None,
        opacity: float = 1.0,
    ) -> str:
        """Create a text node and return its ID."""
        args: Dict[str, Any] = {
            "name": name,
            "content": content,
            "x": x,
            "y": y,
            "fontFamily": font_family,
            "fontSize": font_size,
            "fontWeight": font_weight,
            "fontStyle": font_style,
            "color": color,
            "textAlign": text_align,
            "letterSpacing": letter_spacing,
            "textTransform": text_transform,
            "textDecoration": text_decoration,
            "opacity": opacity,
        }
        if parent_id:
            args["parentId"] = parent_id
        if line_height is not None:
            args["lineHeight"] = line_height
        if width is not None:
            args["width"] = width
        if height is not None:
            args["height"] = height

        result = self.call_tool("create_text", args)
        return _extract_id(result)

    # ── Write tools — Fills and Strokes ────────────────────────────────────

    def set_fill(
        self,
        node_id: str,
        *,
        fill_type: str = "solid",
        color: Optional[str] = None,
        gradient_stops: Optional[List[Dict[str, Any]]] = None,
        gradient_angle: float = 180.0,
        gradient_type: str = "linear",
        image_url: Optional[str] = None,
        image_mode: str = "fill",
        opacity: float = 1.0,
    ) -> None:
        """
        Set or replace the fill on a node.

        fill_type : 'solid' | 'linear-gradient' | 'radial-gradient' | 'image'
        gradient_stops : [{"color": "#hex", "position": 0.0}, ...]
        """
        args: Dict[str, Any] = {
            "nodeId": node_id,
            "fillType": fill_type,
            "opacity": opacity,
        }
        if color:
            args["color"] = color
        if gradient_stops:
            args["gradientStops"] = gradient_stops
            args["gradientAngle"] = gradient_angle
            args["gradientType"] = gradient_type
        if image_url:
            args["imageUrl"] = image_url
            args["imageMode"] = image_mode

        self.call_tool("set_fill", args)

    def add_fill(
        self,
        node_id: str,
        fill_type: str = "solid",
        color: Optional[str] = None,
        gradient_stops: Optional[List[Dict[str, Any]]] = None,
        gradient_angle: float = 180.0,
        opacity: float = 1.0,
    ) -> None:
        """Append a fill layer to a node (for multi-fill support)."""
        args: Dict[str, Any] = {
            "nodeId": node_id,
            "fillType": fill_type,
            "opacity": opacity,
        }
        if color:
            args["color"] = color
        if gradient_stops:
            args["gradientStops"] = gradient_stops
            args["gradientAngle"] = gradient_angle
        try:
            self.call_tool("add_fill", args)
        except PencilToolError:
            # Fall back to set_fill if add_fill is not supported
            self.set_fill(
                node_id,
                fill_type=fill_type,
                color=color,
                gradient_stops=gradient_stops,
                gradient_angle=gradient_angle,
                opacity=opacity,
            )

    def set_stroke(
        self,
        node_id: str,
        *,
        color: str = "#000000",
        width: float = 1.0,
        align: str = "center",  # "inside" | "center" | "outside"
        cap: str = "none",  # "none" | "round" | "square"
        join: str = "miter",  # "miter" | "round" | "bevel"
        dash_pattern: Optional[List[float]] = None,
        opacity: float = 1.0,
    ) -> None:
        """Set the stroke on a node."""
        args: Dict[str, Any] = {
            "nodeId": node_id,
            "color": color,
            "width": width,
            "align": align,
            "cap": cap,
            "join": join,
            "opacity": opacity,
        }
        if dash_pattern:
            args["dashPattern"] = dash_pattern
        try:
            self.call_tool("set_stroke", args)
        except PencilToolError:
            pass

    def remove_stroke(self, node_id: str) -> None:
        """Remove the stroke from a node."""
        try:
            self.call_tool("remove_stroke", {"nodeId": node_id})
        except PencilToolError:
            pass

    # ── Write tools — Effects ──────────────────────────────────────────────

    def add_shadow(
        self,
        node_id: str,
        *,
        color: str = "#00000040",
        offset_x: float = 0.0,
        offset_y: float = 4.0,
        blur: float = 8.0,
        spread: float = 0.0,
        inner: bool = False,
    ) -> None:
        """Add a drop shadow (or inner shadow) effect to a node."""
        args: Dict[str, Any] = {
            "nodeId": node_id,
            "color": color,
            "offsetX": offset_x,
            "offsetY": offset_y,
            "blur": blur,
            "spread": spread,
            "inner": inner,
        }
        try:
            self.call_tool("add_shadow", args)
        except PencilToolError:
            pass

    def add_blur(
        self,
        node_id: str,
        radius: float = 4.0,
        *,
        background: bool = False,
    ) -> None:
        """Add a Gaussian or background blur to a node."""
        args: Dict[str, Any] = {
            "nodeId": node_id,
            "radius": radius,
            "background": background,
        }
        try:
            self.call_tool("add_blur", args)
        except PencilToolError:
            pass

    # ── Write tools — Node operations ─────────────────────────────────────

    def rename_node(self, node_id: str, name: str) -> None:
        """Rename a node."""
        self.call_tool("rename_node", {"nodeId": node_id, "name": name})

    def delete_node(self, node_id: str) -> None:
        """Delete a node by ID."""
        self.call_tool("delete_node", {"nodeId": node_id})

    def delete_nodes(self, node_ids: List[str]) -> None:
        """Delete multiple nodes by ID."""
        try:
            self.call_tool("delete_nodes", {"nodeIds": node_ids})
        except PencilToolError:
            for nid in node_ids:
                try:
                    self.delete_node(nid)
                except PencilToolError:
                    pass

    def move_node(
        self,
        node_id: str,
        new_parent_id: str,
        index: int = -1,
    ) -> None:
        """Move a node to a different parent."""
        args: Dict[str, Any] = {
            "nodeId": node_id,
            "newParentId": new_parent_id,
        }
        if index >= 0:
            args["index"] = index
        self.call_tool("move_node", args)

    def set_position(self, node_id: str, x: float, y: float) -> None:
        """Set absolute position of a node."""
        self.call_tool("set_position", {"nodeId": node_id, "x": x, "y": y})

    def set_size(self, node_id: str, width: float, height: float) -> None:
        """Set the size of a node."""
        self.call_tool(
            "set_size", {"nodeId": node_id, "width": width, "height": height}
        )

    def set_opacity(self, node_id: str, opacity: float) -> None:
        """Set opacity (0.0–1.0)."""
        self.call_tool("set_opacity", {"nodeId": node_id, "opacity": opacity})

    def set_visibility(self, node_id: str, visible: bool) -> None:
        """Show or hide a node."""
        self.call_tool("set_visibility", {"nodeId": node_id, "visible": visible})

    def set_corner_radius(
        self,
        node_id: str,
        radius: float = 0.0,
        *,
        top_left: Optional[float] = None,
        top_right: Optional[float] = None,
        bottom_right: Optional[float] = None,
        bottom_left: Optional[float] = None,
    ) -> None:
        """Set corner radius — uniform or per-corner."""
        args: Dict[str, Any] = {"nodeId": node_id}
        if any(v is not None for v in (top_left, top_right, bottom_right, bottom_left)):
            args["topLeft"] = top_left if top_left is not None else radius
            args["topRight"] = top_right if top_right is not None else radius
            args["bottomRight"] = bottom_right if bottom_right is not None else radius
            args["bottomLeft"] = bottom_left if bottom_left is not None else radius
        else:
            args["radius"] = radius
        try:
            self.call_tool("set_corner_radius", args)
        except PencilToolError:
            pass

    def group_nodes(self, node_ids: List[str], name: str = "Group") -> str:
        """Group multiple nodes and return the group's ID."""
        result = self.call_tool("group_nodes", {"nodeIds": node_ids, "name": name})
        return _extract_id(result)

    def ungroup_node(self, node_id: str) -> List[str]:
        """Ungroup a group node; returns IDs of the ungrouped children."""
        result = self.call_tool("ungroup_node", {"nodeId": node_id})
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("nodeIds", [])
        return []

    # ── Batch operations ───────────────────────────────────────────────────

    def batch_design(
        self,
        operations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Execute a batch of design operations in a single round-trip.

        Each operation dict has the shape::

            {
              "op":   "<create_frame|create_text|set_fill|...>",
              "args": { ... }            # same args as the individual method
              "ref":  "my-local-ref"     # optional — lets you reference the
                                         # new node ID in later ops as "$ref"
            }

        Returns a list of result dicts, one per operation, each with
        at least {"success": bool, "id": str | None}.

        Example
        -------
        ::

            ops = [
                {"op": "create_frame", "args": {"name": "Card", "x": 0, "y": 0,
                                                 "width": 320, "height": 200},
                 "ref": "card"},
                {"op": "create_text",  "args": {"name": "Title", "content": "Hello",
                                                 "parentId": "$card",
                                                 "x": 16, "y": 16}},
            ]
            results = client.batch_design(ops)
        """
        if not self._connected:
            self.connect()

        # Try native batch_design tool first
        try:
            result = self.call_tool("batch_design", {"operations": operations})
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("results", [result])
        except PencilToolError:
            pass

        # Fall back: execute operations sequentially, resolving $refs
        ref_map: Dict[str, str] = {}  # ref-name → resolved node ID
        results: List[Dict[str, Any]] = []

        for op in operations:
            tool = op.get("op", "")
            args = dict(op.get("args", {}))
            ref = op.get("ref", "")

            # Resolve $ref placeholders in args
            _resolve_refs(args, ref_map)

            outcome: Dict[str, Any] = {"op": tool, "success": False, "id": None}
            try:
                raw = self.call_tool(tool, args)
                node_id = _extract_id(raw)
                outcome["success"] = True
                outcome["id"] = node_id
                if ref and node_id:
                    ref_map[ref] = node_id
            except PencilToolError as exc:
                outcome["error"] = str(exc)

            results.append(outcome)

        return results

    # ── Artboard helpers ───────────────────────────────────────────────────

    def get_artboard_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find an artboard by display name (case-insensitive)."""
        for ab in self.list_artboards():
            if ab.get("name", "").lower() == name.lower():
                return ab
        return None

    def get_or_create_artboard(
        self,
        name: str,
        width: float = 390.0,
        height: float = 844.0,
        *,
        background_color: str = "#FFFFFF",
        x: float = 0.0,
        y: float = 0.0,
    ) -> str:
        """Return the ID of an existing artboard or create a new one."""
        existing = self.get_artboard_by_name(name)
        if existing:
            return existing["id"]
        return self.create_artboard(
            name=name,
            x=x,
            y=y,
            width=width,
            height=height,
            background_color=background_color,
        )

    # ── Diagnostics ────────────────────────────────────────────────────────

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"<PencilClient {self.base_url} transport={self._transport} {status}>"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_id(result: Any) -> str:
    """Extract a node ID string from various tool result shapes."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("id", "nodeId", "node_id", "artboardId", "frameId"):
            if key in result:
                return str(result[key])
        # Check nested
        for key in ("node", "artboard", "frame"):
            if isinstance(result.get(key), dict):
                return _extract_id(result[key])
    return ""


def _resolve_refs(args: Dict[str, Any], ref_map: Dict[str, str]) -> None:
    """
    In-place: replace any string value starting with "$" with the
    corresponding resolved node ID from ref_map.

    e.g. args = {"parentId": "$card"}  →  args = {"parentId": "abc-123"}
    """
    for key, val in list(args.items()):
        if isinstance(val, str) and val.startswith("$"):
            ref_name = val[1:]
            if ref_name in ref_map:
                args[key] = ref_map[ref_name]
        elif isinstance(val, dict):
            _resolve_refs(val, ref_map)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    _resolve_refs(item, ref_map)
