"""
Unit tests for Figma Bridge Server (adapters/figma/bridge_server.py).

Tests cover:
- Phase 4: Plugin Discovery (plugin info tracking)
- Phase 5: Error Recovery (retry with backoff)
- Phase 6: Performance (batch operations, font pre-caching)

Note: Async tests use asyncio.run() for simplicity instead of pytest-asyncio.
"""

import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch


def run_async(coro):
    """Helper to run async tests synchronously."""
    return asyncio.new_event_loop().run_until_complete(coro)


class TestBridgeServerConfig:
    """Tests for bridge server configuration constants."""

    def test_default_port(self):
        """Default port is 9223."""
        from adapters.figma.bridge_server import DEFAULT_PORT
        assert DEFAULT_PORT == 9223

    def test_fallback_ports_range(self):
        """Fallback ports are 9224-9232."""
        from adapters.figma.bridge_server import FALLBACK_PORTS
        assert FALLBACK_PORTS == [9224, 9225, 9226, 9227, 9228, 9229, 9230, 9231, 9232]

    def test_retry_config(self):
        """Phase 5: Retry configuration is set."""
        from adapters.figma.bridge_server import MAX_RETRIES, RETRY_BACKOFF_BASE, RETRY_BACKOFF_MULTIPLIER
        assert MAX_RETRIES == 3
        assert RETRY_BACKOFF_BASE == 1.5
        assert RETRY_BACKOFF_MULTIPLIER == 2.0

    def test_batch_config(self):
        """Phase 6: Batch configuration is set."""
        from adapters.figma.bridge_server import BATCH_MAX_OPERATIONS, FONT_PRECACHE_TIMEOUT_MS
        assert BATCH_MAX_OPERATIONS == 50
        assert FONT_PRECACHE_TIMEOUT_MS == 10000


class TestWebSocketFrame:
    """Tests for WebSocket frame parsing and creation."""

    def test_make_ws_frame_text(self):
        """make_ws_frame creates valid text frame."""
        from adapters.figma.bridge_server import make_ws_frame

        payload = b'{"test": "data"}'
        frame = make_ws_frame(payload, opcode=0x01, fin=True)

        # Frame should start with FIN bit set (0x80) | opcode (0x01) = 0x81
        assert frame[0] == 0x81
        # Payload length (13 bytes) should be in second byte
        assert frame[1] == len(payload)
        # Frame should end with payload
        assert frame[2:] == payload

    def test_make_ws_accept_key(self):
        """make_ws_accept_key generates correct accept key."""
        from adapters.figma.bridge_server import make_ws_accept_key

        # Example from RFC 6455
        client_key = "dGhlIHNhbXBsZSBub25jZQ=="
        accept_key = make_ws_accept_key(client_key)

        # Should produce the RFC example accept key
        assert accept_key == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="

    def test_parse_ws_frame_simple(self):
        """parse_ws_frame handles simple text frame."""
        from adapters.figma.bridge_server import parse_ws_frame, make_ws_frame

        payload = b'{"id": "test"}'
        frame_bytes = make_ws_frame(payload, opcode=0x01, fin=True)

        frame, consumed = parse_ws_frame(frame_bytes)

        assert frame.fin is True
        assert frame.opcode == 0x01
        assert frame.payload == payload
        assert consumed == len(frame_bytes)


class TestBridgeServer:
    """Tests for FigmaBridgeServer class."""

    def test_init_default_port(self):
        """Server initializes with default port."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        server = FigmaBridgeServer()
        assert server.port == 9223

    def test_init_custom_port(self):
        """Server initializes with custom port."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        server = FigmaBridgeServer(port=9225)
        assert server.port == 9225

    def test_plugin_info_initial_state(self):
        """Phase 4: Plugin info starts empty."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        server = FigmaBridgeServer()
        assert server._plugin_info == {}
        assert server._plugin_connected_at is None
        assert server._plugin_disconnect_count == 0

    def test_loaded_fonts_initial_state(self):
        """Phase 6: Font cache starts empty."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        server = FigmaBridgeServer()
        assert server._loaded_fonts == set()


class TestPortDiscovery:
    """Tests for port discovery functions."""

    def test_write_port_file_content(self):
        """write_port_file creates valid JSON."""
        from adapters.figma.bridge_server import write_port_file, remove_port_file
        import os

        # Write to temp dir for test isolation
        path = write_port_file(9223)

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            assert data["port"] == 9223
            assert data["pid"] == os.getpid()
            assert data["host"] == "localhost"
            assert "startedAt" in data
            assert data["version"] == "1.0.0"
        finally:
            remove_port_file(9223)

    def test_remove_port_file_safe(self):
        """remove_port_file doesn't raise if file missing."""
        from adapters.figma.bridge_server import remove_port_file

        # Should not raise
        remove_port_file(99999)


class TestPendingRequest:
    """Tests for PendingRequest dataclass."""

    def test_pending_request_fields(self):
        """PendingRequest has required fields."""
        from adapters.figma.bridge_server import PendingRequest

        loop = asyncio.new_event_loop()
        future = loop.create_future()

        req = PendingRequest(request_id="test_123", future=future)

        assert req.request_id == "test_123"
        assert req.future == future
        assert req.created_at > 0

        loop.close()


class TestRespondMethods:
    """Tests for HTTP response methods."""

    def test_respond_json(self):
        """_respond_json sends valid JSON response."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()

            # Mock writer
            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._respond_json(writer, {"status": "ok", "count": 5})

            # Check write was called
            assert writer.write.called
            written_data = writer.write.call_args[0][0]

            # Should contain JSON body
            assert b'"status"' in written_data
            assert b'"count"' in written_data

        run_async(test())

    def test_respond_error_string(self):
        """_respond_error handles string message."""
        from adapters.figma.bridge_server import FigmaBridgeServer
        from http import HTTPStatus

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._respond_error(writer, HTTPStatus.NOT_FOUND, "Not found")

            written_data = writer.write.call_args[0][0]
            assert b"404" in written_data
            assert b"Not Found" in written_data

        run_async(test())

    def test_respond_error_dict(self):
        """_respond_error handles dict message with suggestions."""
        from adapters.figma.bridge_server import FigmaBridgeServer
        from http import HTTPStatus

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            error_msg = {
                "error": "Plugin not connected",
                "suggestions": ["1. Open the plugin", "2. Check connection"],
            }

            await server._respond_error(writer, HTTPStatus.SERVICE_UNAVAILABLE, error_msg)

            written_data = writer.write.call_args[0][0]
            assert b"503" in written_data
            assert b"Plugin not connected" in written_data
            assert b"suggestions" in written_data

        run_async(test())


class TestHandleExecuteErrors:
    """Tests for execute endpoint error handling."""

    def test_invalid_json_returns_400(self):
        """Invalid JSON returns 400 Bad Request."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_execute(writer, b"not valid json")

            written_data = writer.write.call_args[0][0]
            assert b"400" in written_data

        run_async(test())

    def test_missing_code_returns_400(self):
        """Missing code field returns 400 Bad Request."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_execute(writer, b'{"timeout": 5000}')

            written_data = writer.write.call_args[0][0]
            assert b"400" in written_data
            assert b"Missing" in written_data

        run_async(test())

    def test_plugin_not_connected_returns_503(self):
        """Plugin not connected returns 503 with suggestions."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()
            # Don't set ws_connected event

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_execute(writer, b'{"code": "figma.notify()"}')

            written_data = writer.write.call_args[0][0]
            assert b"503" in written_data
            assert b"suggestions" in written_data

        run_async(test())


class TestBatchOperations:
    """Tests for batch endpoint (Phase 6)."""

    def test_batch_missing_operations_returns_400(self):
        """Missing operations field returns 400."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_batch(writer, b'{}')

            written_data = writer.write.call_args[0][0]
            assert b"400" in written_data

        run_async(test())

    def test_batch_empty_operations_returns_400(self):
        """Empty operations returns 400."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_batch(writer, b'{"operations": []}')

            written_data = writer.write.call_args[0][0]
            assert b"400" in written_data

        run_async(test())

    def test_batch_too_many_operations_returns_400(self):
        """Too many operations returns 400."""
        from adapters.figma.bridge_server import FigmaBridgeServer, BATCH_MAX_OPERATIONS

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            ops = [{"code": "figma.notify()"} for _ in range(BATCH_MAX_OPERATIONS + 1)]
            await server._handle_batch(writer, json.dumps({"operations": ops}).encode())

            written_data = writer.write.call_args[0][0]
            assert b"400" in written_data
            assert b"Too many operations" in written_data

        run_async(test())

    def test_batch_plugin_not_connected_returns_503(self):
        """Batch requires plugin connection."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()
            # Don't set ws_connected event

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_batch(
                writer,
                b'{"operations": [{"code": "figma.notify()"}]}'
            )

            written_data = writer.write.call_args[0][0]
            assert b"503" in written_data

        run_async(test())


class TestFontPrecache:
    """Tests for font pre-caching endpoint (Phase 6)."""

    def test_precache_missing_fonts_returns_400(self):
        """Missing fonts field returns 400."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_font_precache(writer, b'{}')

            written_data = writer.write.call_args[0][0]
            assert b"400" in written_data

        run_async(test())

    def test_precache_empty_fonts_returns_400(self):
        """Empty fonts returns 400."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_font_precache(writer, b'{"fonts": []}')

            written_data = writer.write.call_args[0][0]
            assert b"400" in written_data

        run_async(test())

    def test_precache_already_cached(self):
        """Already cached fonts return immediately."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()
            server.ws_connected.set()  # Simulate plugin connected
            server._loaded_fonts.add("Inter")

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_font_precache(writer, b'{"fonts": ["Inter"]}')

            written_data = writer.write.call_args[0][0]
            assert b"already_cached" in written_data

        run_async(test())

    def test_precache_plugin_not_connected_returns_503(self):
        """Font pre-cache requires plugin connection."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()
            # Don't set ws_connected event

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            await server._handle_font_precache(writer, b'{"fonts": ["Inter"]}')

            written_data = writer.write.call_args[0][0]
            assert b"503" in written_data

        run_async(test())


class TestHealthEndpoint:
    """Tests for health endpoint (Phase 4)."""

    def test_health_includes_plugin_info(self):
        """Health endpoint includes plugin info."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()
            server.ws_connected.set()
            server._plugin_info = {"version": "1.0.0", "connected": True}
            server._plugin_connected_at = 1000.0
            server._loaded_fonts.add("Inter")

            writer = MagicMock()
            writer.write = MagicMock()
            writer.drain = MagicMock(return_value=asyncio.sleep(0))

            # Patch time.time to return fixed value
            with patch('time.time', return_value=1100.0):
                await server._handle_http(
                    None, writer, "GET", "/health", {}
                )

            written_data = writer.write.call_args[0][0]

            # Parse JSON body from response
            body_start = written_data.find(b'{')
            body = json.loads(written_data[body_start:])

            assert body["status"] == "ok"
            assert body["plugin_connected"] is True
            assert body["plugin"]["version"] == "1.0.0"
            assert body["plugin_uptime_seconds"] == 100.0
            assert "Inter" in body["loaded_fonts"]

        run_async(test())


class TestRetryLogic:
    """Tests for retry with backoff (Phase 5)."""

    def test_retry_config_values(self):
        """Retry configuration has sensible defaults."""
        from adapters.figma.bridge_server import (
            MAX_RETRIES,
            RETRY_BACKOFF_BASE,
            RETRY_BACKOFF_MULTIPLIER,
        )

        # Should retry 3 times
        assert MAX_RETRIES == 3

        # Backoff should start at 1.5s
        assert RETRY_BACKOFF_BASE == 1.5

        # Backoff should double each time
        assert RETRY_BACKOFF_MULTIPLIER == 2.0

    def test_retry_on_timeout(self):
        """Retry happens on timeout errors."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()
            server.ws_connected.set()

            # Mock _send_to_plugin to fail twice then succeed
            call_count = 0

            async def mock_send(request_id, code, timeout_ms):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise TimeoutError("Test timeout")
                return {"success": True}

            server._send_to_plugin = mock_send

            # Mock sleep to speed up test
            async def mock_sleep(seconds):
                pass

            with patch('asyncio.sleep', side_effect=mock_sleep):
                result = await server._send_to_plugin_with_retry(
                    "test_id", "code", 1000
                )

            assert result == {"success": True}
            assert call_count == 3

        run_async(test())

    def test_no_retry_on_runtime_error(self):
        """No retry when plugin not connected - RuntimeError raised before send."""
        from adapters.figma.bridge_server import FigmaBridgeServer

        async def test():
            server = FigmaBridgeServer()
            # Don't set ws_connected - this should raise immediately

            # Should raise RuntimeError (plugin not connected) before trying to send
            with pytest.raises(RuntimeError, match="not connected"):
                await server._send_to_plugin_with_retry("test_id", "code", 1000)

        run_async(test())
