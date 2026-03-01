#!/usr/bin/env python3
"""
Client for cursor-talk-to-figma-mcp / claude-talk-to-figma-mcp WebSocket server.

This allows executing commands (including execute_code) through the
WebSocket relay to the Figma plugin.

Usage:
    from talk_to_figma_client import TalkToFigmaClient

    client = TalkToFigmaClient(channel="yzlihbhq")
    result = client.execute_code(js_code)
"""

import json
import time
import uuid
import asyncio
import websockets
from typing import Optional, Dict, Any


class TalkToFigmaClient:
    """WebSocket client for cursor-talk-to-figma-mcp."""

    def __init__(self, host: str = "localhost", port: int = 3055, channel: str = None):
        self.host = host
        self.port = port
        self.channel = channel
        self.ws_url = f"ws://{host}:{port}"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._response_handlers: Dict[str, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to the WebSocket server and join the channel."""
        if self.ws is not None:
            return

        self.ws = await websockets.connect(self.ws_url)
        self._receive_task = asyncio.create_task(self._receive_loop())

        # Join the channel
        if self.channel:
            await self._join_channel(self.channel)

    async def _join_channel(self, channel: str):
        """Join a channel to communicate with the Figma plugin."""
        join_msg = {
            "type": "join",
            "channel": channel,
            "id": str(uuid.uuid4())
        }
        await self.ws.send(json.dumps(join_msg))
        # Wait briefly for join confirmation
        await asyncio.sleep(0.2)

    async def _receive_loop(self):
        """Background task to receive messages from the WebSocket."""
        try:
            async for message in self.ws:
                data = json.loads(message)

                # Handle command responses
                if data.get("type") == "broadcast":
                    inner = data.get("message", {})
                    msg_id = inner.get("id")
                    if msg_id and msg_id in self._response_handlers:
                        future = self._response_handlers.pop(msg_id)
                        if not future.done():
                            future.set_result(inner)

                # Handle system messages
                elif data.get("type") == "system":
                    print(f"[System] {data.get('message')}")
        except websockets.ConnectionClosed:
            print("[WebSocket] Connection closed")
        except Exception as e:
            print(f"[Error] Receive loop error: {e}")

    async def send_command(self, command: str, params: Dict[str, Any] = None,
                          timeout: float = 30.0) -> Dict[str, Any]:
        """Send a command to the Figma plugin and wait for response."""
        if not self.ws:
            await self.connect()

        msg_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._response_handlers[msg_id] = future

        message = {
            "type": "message",
            "channel": self.channel,
            "message": {
                "id": msg_id,
                "command": command,
                "params": params or {}
            }
        }

        await self.ws.send(json.dumps(message))

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._response_handlers.pop(msg_id, None)
            raise TimeoutError(f"Command {command} timed out after {timeout}s")

    async def execute_code(self, code: str, timeout: float = 60.0) -> Dict[str, Any]:
        """Execute arbitrary Figma Plugin API code."""
        return await self.send_command("execute_code", {"code": code, "timeout": int(timeout * 1000)}, timeout)

    async def get_document_info(self) -> Dict[str, Any]:
        """Get information about the current Figma document."""
        return await self.send_command("get_document_info")

    async def get_selection(self) -> Dict[str, Any]:
        """Get the current selection in Figma."""
        return await self.send_command("get_selection")

    async def close(self):
        """Close the WebSocket connection."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            await self.ws.close()
            self.ws = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def main():
    """Test the client."""
    import sys

    # Default channel from user's screenshot
    channel = sys.argv[1] if len(sys.argv) > 1 else "yzlihbhq"

    print(f"Connecting to WebSocket on port 3055, channel: {channel}")

    async with TalkToFigmaClient(channel=channel) as client:
        # Test ping
        print("\n1. Testing ping...")
        try:
            result = await client.send_command("ping")
            print(f"   Ping result: {result}")
        except Exception as e:
            print(f"   Ping error: {e}")

        # Get document info
        print("\n2. Getting document info...")
        try:
            result = await client.send_command("get_document_info")
            print(f"   Document: {result.get('result', result)}")
        except Exception as e:
            print(f"   Error: {e}")

        # Execute simple code
        print("\n3. Testing execute_code...")
        test_code = '''
        return {
            currentPageName: figma.currentPage.name,
            nodeCount: figma.currentPage.children.length
        };
        '''
        try:
            result = await client.execute_code(test_code)
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
