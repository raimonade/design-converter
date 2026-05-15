from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import requests

from ptf.mcp_client import PaperMCPClient, BATCH_SIZE

log = logging.getLogger("paper_to_figma")


@dataclass
class TreeNode:
    id: str
    name: str
    component: str  # "Frame", "Text", "Rectangle", etc.
    text_content: str = ""
    node_width: Optional[float] = None
    node_height: Optional[float] = None
    children: list[TreeNode] = field(default_factory=list)
    styles: dict = field(default_factory=dict)
    image_b64: Optional[str] = None


SVG_COMPONENTS = {"SVG", "SVGVisualElement"}


def _export_svg_as_image(client: PaperMCPClient, node_id: str, name: str) -> str:
    """Export SVG node as raster image via get_screenshot, return base64 or empty string."""
    try:
        result = client.call_tool("get_screenshot", {"nodeId": node_id})
        content = result.get("content", []) if isinstance(result, dict) else []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image":
                    data = item.get("data", "")
                    if data:
                        log.info("  Exported SVG '%s' as image (%d KB)", name, len(data) // 1024)
                        return data
    except Exception as e:
        log.warning("  Failed to export SVG '%s': %s", name, e)
    return ""


def build_tree(client: PaperMCPClient, node_id: str, name: str, component: str) -> TreeNode:
    text_content = ""
    node_width = None
    node_height = None
    if component == "Text":
        info = client.call_tool("get_node_info", {"nodeId": node_id})
        text_content = info.get("textContent", name)
        node_width = info.get("width")
        node_height = info.get("height")
    elif component in SVG_COMPONENTS:
        info = client.call_tool("get_node_info", {"nodeId": node_id})
        node_width = info.get("width")
        node_height = info.get("height")
    node = TreeNode(
        id=node_id, name=name, component=component,
        text_content=text_content, node_width=node_width, node_height=node_height,
    )
    if component in SVG_COMPONENTS:
        node.image_b64 = _export_svg_as_image(client, node_id, name)
    if component not in ("Text", *SVG_COMPONENTS):
        children_data = client.get_children(node_id)
        for child in children_data:
            child_node = build_tree(
                client, child["id"], child["name"], child["component"],
            )
            node.children.append(child_node)
    return node


def collect_all_ids(node: TreeNode) -> list[str]:
    ids = [node.id]
    for child in node.children:
        ids.extend(collect_all_ids(child))
    return ids


def attach_styles(client: PaperMCPClient, tree: TreeNode) -> None:
    all_ids = collect_all_ids(tree)
    log.info("  Fetching styles for %d nodes...", len(all_ids))

    all_styles: dict[str, dict] = {}
    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = all_ids[i : i + BATCH_SIZE]
        styles = client.get_computed_styles(batch)
        all_styles.update(styles)

    def _apply(node: TreeNode) -> None:
        node.styles = all_styles.get(node.id, {})
        for child in node.children:
            _apply(child)

    _apply(tree)


def fetch_images(tree: TreeNode) -> None:
    """Walk tree and download any backgroundImage URLs as base64."""

    def _walk(node: TreeNode) -> None:
        bg_image = node.styles.get("backgroundImage", "")
        if bg_image.startswith("url("):
            m = re.match(r"url\(([^)]+)\)", bg_image)
            if m:
                url = m.group(1).strip("'\"")
                try:
                    resp = requests.get(url, timeout=15)
                    resp.raise_for_status()
                    node.image_b64 = base64.b64encode(resp.content).decode("ascii")
                    log.info("  Fetched image for '%s' (%d KB)", node.name, len(resp.content) // 1024)
                except Exception as e:
                    log.warning("  Failed to fetch image for '%s': %s", node.name, e)
        for child in node.children:
            _walk(child)

    _walk(tree)
