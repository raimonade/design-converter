#!/usr/bin/env python3
"""
Execute generated Figma JS code via Desktop Bridge WebSocket.

Usage:
    python3 execute_design.py Paper_[TO-0].js
"""

import sys
import json
import time
import requests

BRIDGE_PORT = 9223
BRIDGE_URL = f"http://localhost:{BRIDGE_PORT}"


def check_health():
    """Check if bridge server is running and plugin is connected."""
    try:
        resp = requests.get(f"{BRIDGE_URL}/health", timeout=2)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def execute_code(code: str, timeout: int = 60000):
    """Execute JS code in Figma via Desktop Bridge."""
    payload = {
        "id": f"exec_{int(time.time() * 1000)}",
        "method": "EXECUTE_CODE",
        "params": {
            "code": code,
            "timeout": timeout
        }
    }

    try:
        resp = requests.post(
            f"{BRIDGE_URL}/execute",
            json=payload,
            timeout=timeout / 1000 + 10
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 execute_design.py <js_file>")
        print("\nExample: python3 execute_design.py Paper_[TO-0].js")
        sys.exit(1)

    js_file = sys.argv[1]

    # Check bridge health
    print(f"Checking bridge server on port {BRIDGE_PORT}...")
    health = check_health()
    print(f"Health: {json.dumps(health, indent=2)}")

    if "error" in health:
        print("\n❌ Bridge server not running or plugin not connected.")
        print("   Start the bridge: python3 -m adapters.figma.bridge_server")
        print("   Then connect the Desktop Bridge plugin in Figma.")
        sys.exit(1)

    if not health.get("plugin_connected"):
        print("\n⚠️  Bridge server running but plugin not connected.")
        print("   Open 'Figma Desktop Bridge' plugin in Figma and connect to port 9223.")
        sys.exit(1)

    # Read JS file
    print(f"\n📖 Reading {js_file}...")
    try:
        with open(js_file, 'r') as f:
            code = f.read()
        print(f"   {len(code)} bytes")
    except FileNotFoundError:
        print(f"❌ File not found: {js_file}")
        sys.exit(1)

    # Execute
    print("\n🚀 Executing code in Figma...")
    result = execute_code(code)
    print(f"Result: {json.dumps(result, indent=2)}")

    if result.get("result", {}).get("success"):
        print("\n✅ Design created in Figma!")
    else:
        print(f"\n❌ Execution failed: {result.get('error') or result.get('result', {}).get('error')}")


if __name__ == "__main__":
    main()
