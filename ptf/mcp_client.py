from __future__ import annotations

import json
import logging
from typing import Optional

import requests

log = logging.getLogger("paper_to_figma")

PAPER_MCP_URL = "http://127.0.0.1:29979/mcp"
BATCH_SIZE = 20


class PaperMCPClient:
    """Talks to Paper's MCP server over HTTP with SSE responses."""

    def __init__(self, url: str = PAPER_MCP_URL) -> None:
        self._url = url
        self._session_id: Optional[str] = None
        self._request_id = 0

    def initialize(self) -> None:
        resp = self._post({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "paper_to_figma", "version": "0.1"},
            },
        })
        sid = resp.headers.get("mcp-session-id")
        if sid:
            self._session_id = sid
            log.info("MCP session: %s", sid)
        else:
            log.warning("No mcp-session-id in response headers")

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        resp = self._post(payload)
        return self._parse_sse(resp)

    def get_basic_info(self) -> dict:
        return self.call_tool("get_basic_info")

    def get_children(self, node_id: str) -> list[dict]:
        result = self.call_tool("get_children", {"nodeId": node_id})
        return result.get("children", [])

    def get_computed_styles(self, node_ids: list[str]) -> dict[str, dict]:
        result = self.call_tool("get_computed_styles", {"nodeIds": node_ids})
        if isinstance(result, dict):
            return {k: v for k, v in result.items() if isinstance(v, dict)}
        return {}

    def _post(self, payload: dict) -> requests.Response:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        resp = requests.post(self._url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp

    def _parse_sse(self, resp: requests.Response) -> dict:
        content_type = resp.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        msg = json.loads(data_str)
                        if "result" in msg:
                            return self._extract_content(msg["result"])
                        if "error" in msg:
                            raise RuntimeError(f"MCP error: {msg['error']}")
                    except json.JSONDecodeError:
                        continue
            raise RuntimeError("No valid JSON-RPC result in SSE response")

        msg = resp.json()
        if "result" in msg:
            return self._extract_content(msg["result"])
        if "error" in msg:
            raise RuntimeError(f"MCP error: {msg['error']}")
        return msg

    def _extract_content(self, result: dict) -> dict:
        content_list = result.get("content", [])
        for item in content_list:
            if item.get("type") == "text":
                text = item["text"]
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
        return result
