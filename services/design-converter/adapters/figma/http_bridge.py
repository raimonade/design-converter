"""
Figma HTTP Bridge Client
========================
Lightweight HTTP client for the figma-bridge-server.

This enables the design-converter to write to Figma via HTTP,
making it symmetric with Paper (HTTP 29979) and Pencil (MCP tools).

Usage:
    from adapters.figma.http_bridge import FigmaBridgeClient

    client = FigmaBridgeClient()
    if client.is_connected():
        result = client.execute_code("figma.createRectangle()")

Error Handling:
    - is_server_running(): Check if bridge server is up (plugin may not be connected)
    - is_connected(): Check if bridge server is up AND plugin is connected
    - execute_code(): Returns BridgeResult with success/error/node_id

The bridge server (bridge_server.py) must be running before using this client.
Start it with: python3 adapters/figma/bridge_server.py --port 9223
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class BridgeResult:
    """Result from a bridge execution."""

    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    node_id: Optional[str] = None

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "BridgeResult":
        return cls(
            success=data.get("success", False) and not data.get("error"),
            result=data.get("result"),
            error=data.get("error"),
            node_id=data.get("result", {}).get("nodeId") if isinstance(data.get("result"), dict) else None,
        )


class FigmaBridgeClient:
    """
    HTTP client for the Figma Bridge Server.

    The bridge server accepts WebSocket connections from the Desktop Bridge
    plugin and exposes an HTTP API for code execution.

    Default port: 9223 (same as figma-console MCP for compatibility)
    """

    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 9223
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._host = host
        self._port = port
        self._base = f"http://{host}:{port}"
        self._timeout = timeout

    # -------------------------------------------------------------------------
    # Connection checks
    # -------------------------------------------------------------------------

    def is_connected(self) -> bool:
        """Check if bridge server is running AND plugin is connected."""
        try:
            resp = self._get("/health")
            return resp.get("status") == "ok" and resp.get("plugin_connected", False)
        except Exception:
            return False

    def is_server_running(self) -> bool:
        """Check if bridge server is running (plugin may not be connected)."""
        try:
            resp = self._get("/health")
            return resp.get("status") == "ok"
        except Exception:
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status for diagnostics.

        Returns dict with:
            - server_running: bool
            - plugin_connected: bool
            - port: int
            - error: str (if any)
            - suggestions: list of str
        """
        result = {
            "server_running": False,
            "plugin_connected": False,
            "port": self._port,
            "error": None,
            "suggestions": [],
        }
        try:
            resp = self._get("/health")
            result["server_running"] = resp.get("status") == "ok"
            result["plugin_connected"] = resp.get("plugin_connected", False)

            if not result["server_running"]:
                result["error"] = "Bridge server not responding"
                result["suggestions"] = [
                    f"Start the bridge server: python3 adapters/figma/bridge_server.py --port {self._port}",
                    f"Or: figma-bridge-server --port {self._port}",
                ]
            elif not result["plugin_connected"]:
                result["error"] = "Desktop Bridge plugin not connected"
                result["suggestions"] = [
                    "1. Open Figma and run the Desktop Bridge plugin",
                    f"2. Configure the plugin to connect to port {self._port}",
                    "3. Wait for the 'Connected' message in the plugin",
                ]
        except urllib.error.URLError as e:
            result["error"] = f"Connection refused: {e.reason}"
            result["suggestions"] = [
                f"The bridge server is not running on port {self._port}",
                f"Start it with: python3 adapters/figma/bridge_server.py --port {self._port}",
            ]
        except Exception as e:
            result["error"] = str(e)
            result["suggestions"] = ["Check network connectivity and server logs"]

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get detailed bridge status."""
        try:
            return self._get("/status")
        except urllib.error.URLError as e:
            return {
                "status": "error",
                "error": f"Connection refused: {e.reason}",
                "port": self._port,
                "server_running": False,
                "plugin_connected": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "port": self._port,
                "server_running": False,
                "plugin_connected": False,
            }

    # -------------------------------------------------------------------------
    # Code execution
    # -------------------------------------------------------------------------

    def execute_code(
        self,
        code: str,
        timeout_ms: int = 30000,
    ) -> BridgeResult:
        """
        Execute JavaScript code in Figma.

        Parameters
        ----------
        code : str
            JavaScript code to execute. Has access to `figma` global.
        timeout_ms : int
            Execution timeout in milliseconds (default: 30000, max: 60000)

        Returns
        -------
        BridgeResult
            Execution result with success/error/node_id.
        """
        try:
            resp = self._post("/execute", {
                "code": code,
                "timeout": min(timeout_ms, 60000),
            })
            return BridgeResult.from_response(resp)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                err_data = json.loads(body)
                return BridgeResult(success=False, error=err_data.get("error", body))
            except json.JSONDecodeError:
                return BridgeResult(success=False, error=f"HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            return BridgeResult(success=False, error=f"Connection failed: {e.reason}")
        except Exception as e:
            return BridgeResult(success=False, error=str(e))

    def execute_and_wait(
        self,
        code: str,
        timeout_ms: int = 30000,
        retries: int = 3,
        retry_delay: float = 1.0,
    ) -> BridgeResult:
        """
        Execute code with automatic retry if plugin not connected.

        Useful when the plugin may still be connecting.
        """
        last_result = None
        for attempt in range(retries):
            result = self.execute_code(code, timeout_ms)
            last_result = result
            if result.success or "not connected" not in str(result.error).lower():
                return result
            time.sleep(retry_delay)
        return last_result

    def wait_for_plugin(self, timeout: float = 30.0, poll_interval: float = 0.5) -> bool:
        """
        Wait for the plugin to connect to the bridge server.

        Parameters
        ----------
        timeout : float
            Maximum seconds to wait (default: 30.0)
        poll_interval : float
            Seconds between checks (default: 0.5)

        Returns
        -------
        bool
            True if plugin connected within timeout, False otherwise
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_connected():
                return True
            time.sleep(poll_interval)
        return False

    # -------------------------------------------------------------------------
    # Convenience methods for common operations
    # -------------------------------------------------------------------------

    def create_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str = "Rectangle",
        fill_color: Optional[str] = None,
        corner_radius: float = 0,
        parent_id: Optional[str] = None,
    ) -> BridgeResult:
        """Create a rectangle in Figma."""
        fill_code = ""
        if fill_color:
            r, g, b = self._hex_to_rgb(fill_color)
            fill_code = f"n.fills=[{{type:'SOLID',color:{{r:{r},g:{g},b:{b},a:1}}}}];"

        parent_code = f'figma.getNodeById("{parent_id}")' if parent_id else "figma.currentPage"

        code = f"""
(async()=>{{
  const parent = {parent_code} || figma.currentPage;
  const n = figma.createRectangle();
  parent.appendChild(n);
  n.name = "{name}";
  n.x = {x};
  n.y = {y};
  n.resize({width}, {height});
  n.cornerRadius = {corner_radius};
  {fill_code}
  return {{success: true, nodeId: n.id}};
}})()
"""
        return self.execute_code(code.strip())

    def create_frame(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill_color: Optional[str] = None,
        layout: str = "NONE",
        parent_id: Optional[str] = None,
    ) -> BridgeResult:
        """Create a frame in Figma."""
        fill_code = ""
        if fill_color:
            r, g, b = self._hex_to_rgb(fill_color)
            fill_code = f"n.fills=[{{type:'SOLID',color:{{r:{r},g:{g},b:{b},a:1}}}}];"

        parent_code = f'figma.getNodeById("{parent_id}")' if parent_id else "figma.currentPage"
        layout_code = f'n.layoutMode = "{layout}";' if layout != "NONE" else ""

        code = f"""
(async()=>{{
  const parent = {parent_code} || figma.currentPage;
  const n = figma.createFrame();
  parent.appendChild(n);
  n.name = "{name}";
  n.x = {x};
  n.y = {y};
  n.resize({width}, {height});
  {layout_code}
  {fill_code}
  return {{success: true, nodeId: n.id}};
}})()
"""
        return self.execute_code(code.strip())

    def create_text(
        self,
        content: str,
        x: float,
        y: float,
        *,
        font_size: float = 14,
        font_name: str = "Inter",
        fill_color: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> BridgeResult:
        """Create a text node in Figma."""
        fill_code = ""
        if fill_color:
            r, g, b = self._hex_to_rgb(fill_color)
            fill_code = f"n.fills=[{{type:'SOLID',color:{{r:{r},g:{g},b:{b},a:1}}}}];"

        parent_code = f'figma.getNodeById("{parent_id}")' if parent_id else "figma.currentPage"
        escaped_content = content.replace("\\", "\\\\").replace('"', '\\"')

        code = f"""
(async()=>{{
  const parent = {parent_code} || figma.currentPage;
  const n = figma.createText();
  parent.appendChild(n);
  await figma.loadFontAsync({{family: "{font_name}", style: "Regular"}});
  n.characters = "{escaped_content}";
  n.fontSize = {font_size};
  n.fontName = {{family: "{font_name}", style: "Regular"}};
  n.x = {x};
  n.y = {y};
  {fill_code}
  return {{success: true, nodeId: n.id}};
}})()
"""
        return self.execute_code(code.strip())

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self._base}{path}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base}{path}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB (0-1 range)."""
        hex_color = hex_color.lstrip("#")
        return (
            int(hex_color[0:2], 16) / 255,
            int(hex_color[2:4], 16) / 255,
            int(hex_color[4:6], 16) / 255,
        )
