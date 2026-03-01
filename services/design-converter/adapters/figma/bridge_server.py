#!/usr/bin/env python3
"""
Figma Bridge Server
===================
A standalone HTTP + WebSocket server that bridges any HTTP client to Figma.

Architecture:
    HTTP Client (any)  →  POST /execute  →  Bridge Server  →  WebSocket  →  Desktop Bridge Plugin  →  Figma

This solves the MCP stdio limitation where only ONE client can use figma-console-mcp.
With this bridge, ANY tool can send code to Figma via simple HTTP POST.

Usage:
    # Start the bridge (Desktop Bridge plugin will auto-connect)
    python bridge_server.py --port 9223

    # Execute code in Figma
    curl -X POST http://localhost:9223/execute \
        -H "Content-Type: application/json" \
        -d '{"code": "figma.notify(\"Hello!\")"}'

    # Check health with plugin info
    curl http://localhost:9223/health

    # Batch execute (Phase 6)
    curl -X POST http://localhost:9223/batch \
        -H "Content-Type: application/json" \
        -d '{"operations": [{"code": "..."}, {"code": "..."}]}'

CLI Usage:
    figma-bridge-server --port 9223 --fallback-ports 9224,9225

Features:
    - Plugin Discovery (Phase 4): Auto-detect plugin connect/disconnect
    - Error Recovery (Phase 5): Retry with backoff, helpful error messages
    - Performance (Phase 6): Batch operations, font pre-caching
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PORT = 9223
FALLBACK_PORTS = [9224, 9225, 9226, 9227, 9228, 9229, 9230, 9231, 9232]
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
PORT_FILE_DIR = "/tmp"
PORT_FILE_PREFIX = "figma-bridge-"
DEFAULT_TIMEOUT_MS = 30000
MAX_TIMEOUT_MS = 60000

# Phase 5: Error Recovery
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5  # seconds
RETRY_BACKOFF_MULTIPLIER = 2.0

# Phase 6: Performance
BATCH_MAX_OPERATIONS = 50
FONT_PRECACHE_TIMEOUT_MS = 10000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("figma-bridge")


# ---------------------------------------------------------------------------
# Port Discovery (for plugin to find us)
# ---------------------------------------------------------------------------


def write_port_file(port: int) -> str:
    """Write a port advertisement file so the plugin can find us."""
    path = f"{PORT_FILE_DIR}/{PORT_FILE_PREFIX}{port}.json"
    data = {
        "port": port,
        "pid": os.getpid(),
        "host": "localhost",
        "startedAt": datetime.now().isoformat(),
        "version": "1.0.0",
    }
    with open(path, "w") as f:
        json.dump(data, f)
    log.info(f"Port file written: {path}")
    return path


def remove_port_file(port: int) -> None:
    """Remove the port advertisement file."""
    path = f"{PORT_FILE_DIR}/{PORT_FILE_PREFIX}{port}.json"
    try:
        os.remove(path)
        log.info(f"Port file removed: {path}")
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# WebSocket Frame Handling (RFC 6455)
# ---------------------------------------------------------------------------


def make_ws_accept_key(client_key: str) -> str:
    """Generate the Sec-WebSocket-Accept header value."""
    return base64.b64encode(
        hashlib.sha1((client_key + WS_MAGIC).encode()).digest()
    ).decode()


@dataclass
class WSFrame:
    """Parsed WebSocket frame."""

    fin: bool
    opcode: int
    masked: bool
    payload: bytes


def parse_ws_frame(data: bytes) -> Tuple[WSFrame, int]:
    """Parse a WebSocket frame from raw bytes. Returns (frame, bytes_consumed)."""
    if len(data) < 2:
        raise ValueError("Incomplete frame header")

    fin = bool(data[0] & 0x80)
    opcode = data[0] & 0x0F
    masked = bool(data[1] & 0x80)
    payload_len = data[1] & 0x7F

    offset = 2
    if payload_len == 126:
        if len(data) < offset + 2:
            raise ValueError("Incomplete extended length")
        payload_len = int.from_bytes(data[offset : offset + 2], "big")
        offset += 2
    elif payload_len == 127:
        if len(data) < offset + 8:
            raise ValueError("Incomplete extended length")
        payload_len = int.from_bytes(data[offset : offset + 8], "big")
        offset += 8

    if masked:
        if len(data) < offset + 4:
            raise ValueError("Incomplete mask")
        mask = data[offset : offset + 4]
        offset += 4

    if len(data) < offset + payload_len:
        raise ValueError("Incomplete payload")

    payload = data[offset : offset + payload_len]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

    return WSFrame(fin=fin, opcode=opcode, masked=masked, payload=payload), offset + payload_len


def make_ws_frame(payload: bytes, opcode: int = 0x01, fin: bool = True) -> bytes:
    """Create a WebSocket text frame."""
    frame = bytearray()
    frame.append(0x80 | opcode if fin else opcode)

    length = len(payload)
    if length <= 125:
        frame.append(length)
    elif length <= 65535:
        frame.append(126)
        frame.extend(length.to_bytes(2, "big"))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, "big"))

    frame.extend(payload)
    return bytes(frame)


# ---------------------------------------------------------------------------
# Bridge Server
# ---------------------------------------------------------------------------


@dataclass
class PendingRequest:
    """A pending HTTP request waiting for WebSocket response."""

    request_id: str
    future: asyncio.Future
    created_at: float = field(default_factory=time.time)


class FigmaBridgeServer:
    """
    HTTP + WebSocket server that bridges HTTP clients to Figma.

    Protocol:
        1. Desktop Bridge plugin connects via WebSocket
        2. HTTP clients POST /execute with {"code": "..."}
        3. Server forwards to plugin via WebSocket
        4. Plugin executes in Figma and responds
        5. Server responds to HTTP client

    Phase 4 - Plugin Discovery:
        - Tracks plugin metadata (version, connected_at, variables)
        - Detects VARIABLES_DATA broadcast on connect
        - Health endpoint includes plugin status

    Phase 5 - Error Recovery:
        - Automatic retry with exponential backoff
        - Helpful error messages with suggestions

    Phase 6 - Performance:
        - Batch operations via /batch endpoint
        - Font pre-caching support
    """

    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.ws_client: Optional[asyncio.StreamReader] = None
        self.ws_writer: Optional[asyncio.StreamWriter] = None
        self.ws_connected = asyncio.Event()
        self.pending_requests: Dict[str, PendingRequest] = {}
        self._running = False
        self._ws_recv_task: Optional[asyncio.Task] = None

        # Phase 4: Plugin Discovery
        self._plugin_info: Dict[str, Any] = {}
        self._plugin_connected_at: Optional[float] = None
        self._plugin_disconnect_count: int = 0

        # Phase 6: Performance - font cache
        self._loaded_fonts: set = set()

    async def start(self) -> None:
        """Start the server."""
        self.server = await asyncio.start_server(
            self._handle_connection,
            "127.0.0.1",
            self.port,
            reuse_address=True,
        )
        self._running = True
        write_port_file(self.port)

        log.info(f"🚀 Figma Bridge Server started on port {self.port}")
        log.info(f"   Waiting for Desktop Bridge plugin to connect...")

        addrs = ", ".join(str(sock.getsockname()) for sock in self.server.sockets)
        log.info(f"   Listening on: {addrs}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self) -> None:
        """Stop the server."""
        self._running = False
        if self._ws_recv_task:
            self._ws_recv_task.cancel()
        if self.ws_writer:
            self.ws_writer.close()
            try:
                await self.ws_writer.wait_closed()
            except Exception:
                pass
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        remove_port_file(self.port)
        log.info("Server stopped")

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming TCP connection (HTTP or WebSocket upgrade)."""
        addr = writer.get_extra_info("peername")
        log.debug(f"Connection from {addr}")

        try:
            # Read HTTP request headers
            headers_raw = b""
            while b"\r\n\r\n" not in headers_raw:
                chunk = await reader.read(1024)
                if not chunk:
                    return
                headers_raw += chunk

            headers_text = headers_raw.decode("utf-8", errors="replace")
            lines = headers_text.split("\r\n")
            request_line = lines[0]
            method, path, _ = request_line.split(" ", 2)

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            # WebSocket upgrade?
            upgrade = headers.get("upgrade", "").lower()
            if upgrade == "websocket":
                await self._handle_ws_upgrade(reader, writer, headers)
                return

            # Regular HTTP request
            await self._handle_http(reader, writer, method, path, headers)

        except Exception as e:
            log.error(f"Connection error: {e}")
        finally:
            # Don't close WebSocket connections here
            if writer != self.ws_writer:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

    async def _handle_ws_upgrade(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        headers: Dict[str, str],
    ) -> None:
        """Handle WebSocket upgrade request from Desktop Bridge plugin."""
        # Already have a client?
        if self.ws_writer:
            log.warning("WebSocket client already connected, replacing...")
            self._plugin_disconnect_count += 1

        client_key = headers.get("sec-websocket-key", "")
        accept_key = make_ws_accept_key(client_key)

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n"
            "\r\n"
        )
        writer.write(response.encode())
        await writer.drain()

        self.ws_client = reader
        self.ws_writer = writer
        self.ws_connected.set()

        # Phase 4: Track plugin connection time
        self._plugin_connected_at = time.time()
        self._plugin_info = {
            "connected": True,
            "connected_at": datetime.now().isoformat(),
            "version": "unknown",  # Will be updated on VARIABLES_DATA
        }

        log.info(f"✅ Desktop Bridge plugin connected! (connection #{self._plugin_disconnect_count + 1})")

        # Start receiving messages
        self._ws_recv_task = asyncio.create_task(self._ws_receive_loop())

    async def _ws_receive_loop(self) -> None:
        """Receive and process WebSocket messages from the plugin."""
        buffer = b""
        try:
            while self._running:
                chunk = await self.ws_client.read(4096)
                if not chunk:
                    log.warning("WebSocket connection closed by plugin")
                    break

                buffer += chunk

                # Parse all complete frames
                while buffer:
                    try:
                        frame, consumed = parse_ws_frame(buffer)
                        buffer = buffer[consumed:]

                        if frame.opcode == 0x08:  # Close frame
                            log.info("WebSocket close frame received")
                            return

                        if frame.opcode in (0x01, 0x02):  # Text or Binary
                            await self._handle_ws_message(frame.payload)

                    except ValueError as e:
                        # Incomplete frame, wait for more data
                        if "Incomplete" in str(e):
                            break
                        log.error(f"Frame parse error: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"WebSocket receive error: {e}")
        finally:
            # Phase 4: Clear plugin info on disconnect
            self.ws_connected.clear()
            self.ws_client = None
            self.ws_writer = None
            self._plugin_info = {
                "connected": False,
                "disconnected_at": datetime.now().isoformat(),
                "previous_connection_duration": (
                    time.time() - self._plugin_connected_at
                    if self._plugin_connected_at else 0
                ),
            }
            self._plugin_connected_at = None
            self._loaded_fonts.clear()  # Phase 6: Clear font cache
            log.info("WebSocket disconnected")

    async def _handle_ws_message(self, payload: bytes) -> None:
        """Handle a message from the Figma plugin."""
        try:
            data = json.loads(payload.decode("utf-8"))
            request_id = data.get("id")
            method = data.get("method")

            # Phase 4: Detect VARIABLES_DATA broadcast from plugin on connect
            if method == "VARIABLES_DATA":
                log.info("📊 Received VARIABLES_DATA from plugin")
                self._plugin_info.update({
                    "variables_count": len(data.get("params", {}).get("variables", [])),
                    "collections_count": len(data.get("params", {}).get("collections", [])),
                    "version": data.get("params", {}).get("version", "unknown"),
                })
                return

            # Phase 4: Detect plugin info broadcast
            if method == "PLUGIN_INFO":
                log.info("📋 Received PLUGIN_INFO from plugin")
                self._plugin_info.update(data.get("params", {}))
                return

            if request_id and request_id in self.pending_requests:
                pending = self.pending_requests.pop(request_id)
                if not pending.future.done():
                    pending.future.set_result(data)
                log.debug(f"Response received for request {request_id}")
            else:
                log.debug(f"Received message without matching request: {data}")

        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON from plugin: {e}")

    async def _send_to_plugin(self, request_id: str, code: str, timeout_ms: int) -> Dict:
        """Send code to the plugin and wait for response."""
        if not self.ws_connected.is_set():
            raise RuntimeError("Desktop Bridge plugin not connected")

        payload = json.dumps({
            "id": request_id,
            "method": "EXECUTE_CODE",
            "params": {"code": code, "timeout": timeout_ms},
        })

        frame = make_ws_frame(payload.encode("utf-8"))
        self.ws_writer.write(frame)
        await self.ws_writer.drain()

        # Create pending request
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.pending_requests[request_id] = PendingRequest(
            request_id=request_id,
            future=future,
        )

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=timeout_ms / 1000 + 5)
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise TimeoutError(f"No response from Figma within {timeout_ms}ms")

    async def _send_to_plugin_with_retry(
        self, request_id: str, code: str, timeout_ms: int, max_retries: int = MAX_RETRIES
    ) -> Dict:
        """
        Phase 5: Send code to plugin with automatic retry on failure.

        Uses exponential backoff: 1.5s, 3s, 6s
        """
        last_error: Optional[Exception] = None
        backoff = RETRY_BACKOFF_BASE

        for attempt in range(max_retries):
            try:
                if not self.ws_connected.is_set():
                    raise RuntimeError("Desktop Bridge plugin not connected")

                return await self._send_to_plugin(request_id, code, timeout_ms)

            except TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    log.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= RETRY_BACKOFF_MULTIPLIER
                    request_id = f"req_{uuid.uuid4().hex[:8]}_{int(time.time()*1000)}"

            except RuntimeError as e:
                # Plugin not connected - don't retry, just fail
                raise

        # All retries exhausted
        raise TimeoutError(
            f"Failed after {max_retries} attempts. Last error: {last_error}. "
            f"Try: (1) Restart the Desktop Bridge plugin in Figma, "
            f"(2) Check Figma Console for errors."
        )

    async def _handle_http(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        method: str,
        path: str,
        headers: Dict[str, str],
    ) -> None:
        """Handle HTTP request."""
        # Read body if present
        body = b""
        content_length = int(headers.get("content-length", 0))
        if content_length > 0:
            body = await reader.read(content_length)

        # Route
        if path == "/health":
            # Phase 4: Enhanced health endpoint with plugin info
            uptime = (
                time.time() - self._plugin_connected_at
                if self._plugin_connected_at else 0
            )
            await self._respond_json(
                writer,
                {
                    "status": "ok",
                    "plugin_connected": self.ws_connected.is_set(),
                    "plugin": self._plugin_info,
                    "plugin_uptime_seconds": round(uptime, 1),
                    "plugin_disconnect_count": self._plugin_disconnect_count,
                    "port": self.port,
                    "pending_requests": len(self.pending_requests),
                    "loaded_fonts": list(self._loaded_fonts),
                },
            )
        elif path == "/execute" and method == "POST":
            await self._handle_execute(writer, body)
        elif path == "/batch" and method == "POST":
            # Phase 6: Batch operations
            await self._handle_batch(writer, body)
        elif path == "/fonts/precache" and method == "POST":
            # Phase 6: Font pre-caching
            await self._handle_font_precache(writer, body)
        elif path == "/status":
            await self._respond_json(
                writer,
                {
                    "status": "ok",
                    "plugin_connected": self.ws_connected.is_set(),
                    "plugin": self._plugin_info,
                    "port": self.port,
                    "pid": os.getpid(),
                },
            )
        else:
            await self._respond_error(writer, HTTPStatus.NOT_FOUND, "Not found")

    async def _handle_execute(self, writer: asyncio.StreamWriter, body: bytes) -> None:
        """Handle POST /execute request."""
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            await self._respond_error(writer, HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        code = data.get("code")
        if not code:
            await self._respond_error(
                writer, HTTPStatus.BAD_REQUEST, "Missing 'code' field"
            )
            return

        timeout_ms = min(data.get("timeout", DEFAULT_TIMEOUT_MS), MAX_TIMEOUT_MS)
        use_retry = data.get("retry", True)  # Phase 5: Enable retry by default
        request_id = f"req_{uuid.uuid4().hex[:8]}_{int(time.time()*1000)}"

        if not self.ws_connected.is_set():
            # Phase 5: Helpful error message
            await self._respond_error(
                writer,
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": "Desktop Bridge plugin not connected",
                    "suggestions": [
                        "1. Open Figma and run the Desktop Bridge plugin",
                        "2. Check the plugin is connected to port " + str(self.port),
                        "3. Verify the server is running: figma-bridge-server --status",
                    ],
                    "server_port": self.port,
                    "server_pid": os.getpid(),
                },
            )
            return

        try:
            # Phase 5: Use retry wrapper
            if use_retry:
                result = await self._send_to_plugin_with_retry(request_id, code, timeout_ms)
            else:
                result = await self._send_to_plugin(request_id, code, timeout_ms)
            await self._respond_json(writer, result)
        except TimeoutError as e:
            await self._respond_error(writer, HTTPStatus.GATEWAY_TIMEOUT, str(e))
        except RuntimeError as e:
            await self._respond_error(writer, HTTPStatus.SERVICE_UNAVAILABLE, str(e))
        except Exception as e:
            await self._respond_error(
                writer, HTTPStatus.INTERNAL_SERVER_ERROR, str(e)
            )

    async def _handle_batch(self, writer: asyncio.StreamWriter, body: bytes) -> None:
        """
        Phase 6: Handle POST /batch request for multiple operations.

        Request format:
        {
            "operations": [
                {"code": "figma.createRectangle()"},
                {"code": "figma.createFrame()"}
            ],
            "stop_on_error": false,
            "timeout": 30000
        }
        """
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            await self._respond_error(writer, HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        operations = data.get("operations", [])
        if not operations:
            await self._respond_error(
                writer, HTTPStatus.BAD_REQUEST, "Missing 'operations' field"
            )
            return

        if len(operations) > BATCH_MAX_OPERATIONS:
            await self._respond_error(
                writer,
                HTTPStatus.BAD_REQUEST,
                f"Too many operations: {len(operations)} > {BATCH_MAX_OPERATIONS}",
            )
            return

        if not self.ws_connected.is_set():
            await self._respond_error(
                writer,
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": "Desktop Bridge plugin not connected",
                    "suggestions": [
                        "1. Open Figma and run the Desktop Bridge plugin",
                        "2. Check the plugin is connected to port " + str(self.port),
                    ],
                },
            )
            return

        stop_on_error = data.get("stop_on_error", False)
        timeout_ms = min(data.get("timeout", DEFAULT_TIMEOUT_MS), MAX_TIMEOUT_MS)

        results = []
        for i, op in enumerate(operations):
            code = op.get("code")
            if not code:
                results.append({
                    "index": i,
                    "success": False,
                    "error": "Missing 'code' field",
                })
                if stop_on_error:
                    break
                continue

            request_id = f"batch_{i}_{uuid.uuid4().hex[:8]}_{int(time.time()*1000)}"

            try:
                result = await self._send_to_plugin_with_retry(request_id, code, timeout_ms)
                results.append({
                    "index": i,
                    "success": True,
                    "result": result,
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": str(e),
                })
                if stop_on_error:
                    break

        await self._respond_json(writer, {
            "total": len(operations),
            "completed": len(results),
            "results": results,
        })

    async def _handle_font_precache(self, writer: asyncio.StreamWriter, body: bytes) -> None:
        """
        Phase 6: Handle POST /fonts/precache to pre-load fonts.

        Request format:
        {
            "fonts": ["Inter", "Roboto"]
        }
        """
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            await self._respond_error(writer, HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        fonts = data.get("fonts", [])
        if not fonts:
            await self._respond_error(
                writer, HTTPStatus.BAD_REQUEST, "Missing 'fonts' field"
            )
            return

        if not self.ws_connected.is_set():
            await self._respond_error(
                writer,
                HTTPStatus.SERVICE_UNAVAILABLE,
                "Desktop Bridge plugin not connected",
            )
            return

        # Generate code to load fonts
        font_loads = []
        for font in fonts:
            if font not in self._loaded_fonts:
                font_loads.append(f'figma.loadFontAsync({{"family": "{font}", "style": "Regular"}})')
                self._loaded_fonts.add(font)

        if not font_loads:
            await self._respond_json(writer, {
                "status": "already_cached",
                "fonts": list(self._loaded_fonts),
            })
            return

        code = f"Promise.all([{', '.join(font_loads)}]).then(() => {{ return 'loaded'; }})"
        request_id = f"fonts_{uuid.uuid4().hex[:8]}_{int(time.time()*1000)}"

        try:
            result = await self._send_to_plugin_with_retry(
                request_id, code, FONT_PRECACHE_TIMEOUT_MS
            )
            await self._respond_json(writer, {
                "status": "loaded",
                "fonts": list(self._loaded_fonts),
                "result": result,
            })
        except Exception as e:
            await self._respond_error(
                writer, HTTPStatus.INTERNAL_SERVER_ERROR, str(e)
            )

    async def _respond_json(self, writer: asyncio.StreamWriter, data: Dict) -> None:
        """Send JSON response."""
        body = json.dumps(data).encode("utf-8")
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        writer.write(response.encode() + body)
        await writer.drain()

    async def _respond_error(
        self, writer: asyncio.StreamWriter, status: HTTPStatus, message
    ) -> None:
        """Send error response. Message can be string or dict."""
        if isinstance(message, dict):
            body = json.dumps(message).encode("utf-8")
        else:
            body = json.dumps({"error": message, "status": status.phrase}).encode("utf-8")
        response = (
            f"HTTP/1.1 {status.value} {status.phrase}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        writer.write(response.encode() + body)
        await writer.drain()


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def find_available_port(start_port: int, fallbacks: List[int]) -> int:
    """Find an available port."""
    import socket

    for port in [start_port] + fallbacks:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports in range {start_port}-{fallbacks[-1]}")


async def main_async(port: int, fallback_ports: List[int]) -> None:
    """Async main entry point."""
    actual_port = find_available_port(port, fallback_ports)
    if actual_port != port:
        log.info(f"Port {port} in use, using {actual_port}")

    server = FigmaBridgeServer(port=actual_port)

    def signal_handler(sig, frame):
        log.info("Shutting down...")
        asyncio.create_task(server.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await server.start()
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Figma Bridge Server - HTTP to Figma plugin bridge"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--fallback-ports",
        type=str,
        default=",".join(map(str, FALLBACK_PORTS)),
        help="Comma-separated fallback ports",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    fallbacks = [int(p.strip()) for p in args.fallback_ports.split(",")]

    asyncio.run(main_async(args.port, fallbacks))


if __name__ == "__main__":
    main()
