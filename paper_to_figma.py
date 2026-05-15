"""
paper_to_figma.py — Convert Paper Design artboards to Figma

Reads Paper's design tree via its MCP HTTP API, generates Figma Plugin API
JavaScript, and pushes via the persistent bridge server (bridge_server.py).

Usage:
    # First, start the bridge server (once):
    .venv/bin/python3 services/design-converter/adapters/figma/bridge_server.py --port 9223
    # Then connect Desktop Bridge plugin to port 9223.

    # Convert artboards (no reconnection needed):
    .venv/bin/python3 paper_to_figma.py --artboard X6-0
    .venv/bin/python3 paper_to_figma.py --artboard X6-0 --dry-run
    .venv/bin/python3 paper_to_figma.py                        # all artboards
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests

from ptf import PaperMCPClient, build_tree, attach_styles, fetch_images, FigmaCodeGen

log = logging.getLogger("paper_to_figma")

BRIDGE_URL = "http://127.0.0.1:{port}"


def push_to_bridge(js_code: str, port: int, timeout_ms: int = 120000) -> dict:
    url = f"{BRIDGE_URL.format(port=port)}/execute"
    resp = requests.post(
        url,
        json={"code": js_code, "timeout": timeout_ms, "retry": True},
        timeout=timeout_ms / 1000 + 10,
    )
    resp.raise_for_status()
    return resp.json()


def check_bridge(port: int) -> bool:
    try:
        resp = requests.get(f"{BRIDGE_URL.format(port=port)}/health", timeout=3)
        data = resp.json()
        connected = data.get("plugin_connected", False)
        if not connected:
            log.error("Bridge server running but plugin not connected on port %d", port)
        return connected
    except requests.ConnectionError:
        return False


def convert_artboard(client: PaperMCPClient, artboard: dict) -> str:
    artboard_id = artboard["id"]
    name = artboard["name"]
    width = artboard["width"]
    height = artboard["height"]

    log.info("Building tree for '%s' (%s)...", name, artboard_id)
    tree = build_tree(client, artboard_id, name, "Frame")
    attach_styles(client, tree)
    fetch_images(tree)

    log.info("Generating Figma JS for '%s'...", name)
    gen = FigmaCodeGen()
    return gen.generate(tree, width, height)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Paper Design artboards to Figma"
    )
    parser.add_argument(
        "--artboard",
        help="Specific artboard ID to convert (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Output generated JS without pushing to Figma",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9223,
        help="Bridge server port (default: 9223)",
    )
    parser.add_argument(
        "--output",
        help="Save JS to file instead of stdout (with --dry-run)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    log.info("Connecting to Paper MCP...")
    try:
        client = PaperMCPClient()
        client.initialize()
    except requests.ConnectionError:
        log.error("Cannot connect to Paper MCP. Is Paper Design running?")
        sys.exit(1)

    info = client.get_basic_info()
    artboards = info.get("artboards", [])
    log.info(
        "Found %d artboards in '%s'",
        len(artboards),
        info.get("fileName", "?"),
    )

    if args.artboard:
        artboards = [a for a in artboards if a["id"] == args.artboard]
        if not artboards:
            log.error("Artboard '%s' not found", args.artboard)
            available = ", ".join(
                f"{a['id']} ({a['name']})" for a in info.get("artboards", [])
            )
            log.error("Available: %s", available)
            sys.exit(1)

    js_outputs: list[tuple[str, str]] = []
    for artboard in artboards:
        js_code = convert_artboard(client, artboard)
        js_outputs.append((artboard["name"], js_code))
        log.info(
            "Generated %d bytes of JS for '%s'",
            len(js_code),
            artboard["name"],
        )

    if args.dry_run:
        for name, js_code in js_outputs:
            if args.output:
                out_path = Path(args.output)
                if len(js_outputs) > 1:
                    safe_name = re.sub(r"[^\w\-.]", "_", name)
                    out_path = out_path.parent / f"{safe_name}.js"
                out_path.write_text(js_code, encoding="utf-8")
                log.info("Saved: %s", out_path)
            else:
                print(f"// === {name} ===")
                print(js_code)
                print()
        return

    if not check_bridge(args.port):
        log.error(
            "Bridge server not available on port %d.\n"
            "  Start it:  .venv/bin/python3 services/design-converter/adapters/figma/bridge_server.py --port %d\n"
            "  Then connect the Desktop Bridge plugin to port %d.",
            args.port, args.port, args.port,
        )
        sys.exit(1)

    log.info("Bridge connected on port %d", args.port)

    for name, js_code in js_outputs:
        log.info("Pushing '%s' (%d KB)...", name, len(js_code) // 1024)
        t0 = time.time()
        try:
            response = push_to_bridge(js_code, args.port)
            elapsed = time.time() - t0

            result = response.get("result", {})
            if isinstance(result, dict) and result.get("success"):
                log.info(
                    "Created '%s' (nodeId=%s) in %.1fs",
                    result.get("nodeName", name),
                    result.get("nodeId", "?"),
                    elapsed,
                )
            else:
                error = (
                    result.get("error", "")
                    if isinstance(result, dict)
                    else response.get("error", str(response))
                )
                log.error("Failed to create '%s': %s", name, error)
        except requests.ConnectionError:
            log.error("Lost connection to bridge server")
            sys.exit(1)
        except requests.Timeout:
            log.error("Timeout pushing '%s'", name)
        except Exception as e:
            log.error("Error pushing '%s': %s", name, e)

    log.info("Done.")


if __name__ == "__main__":
    main()
