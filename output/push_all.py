#!/usr/bin/env python3
"""Push all generated .js scripts to Figma via Desktop Bridge WebSocket."""

import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'design-converter'))

from pathlib import Path

# Use the same bridge protocol as FigmaWriter
OUTPUT_DIR = Path(__file__).parent.parent / "output-v2"
SCRIPTS = sorted(OUTPUT_DIR.glob("*.js"))

if not SCRIPTS:
    print("No Paper_*.js scripts found in output/")
    sys.exit(1)

print(f"Found {len(SCRIPTS)} scripts to push.")
print("Starting WebSocket server on port 9224...")
print(">>> In the Desktop Bridge plugin, select port 9224 and click Connect <<<\n")

# Import the bridge class from the writer module
from adapters.figma.writer import _DesktopBridge

bridge = _DesktopBridge(port=9224, connect_timeout=60.0)
bridge.start()
print("Plugin connected!\n")

success = 0
fail = 0

for script_path in SCRIPTS:
    name = script_path.stem
    code = script_path.read_text()
    size_kb = len(code) / 1024

    print(f"  Pushing {name} ({size_kb:.0f}KB)...", end=" ", flush=True)
    try:
        response = bridge.execute_code(code, timeout_ms=60000)
        if "error" in response:
            print(f"FAIL: {response['error']}")
            fail += 1
        else:
            result = response.get("result", {})
            node_id = result.get("nodeId", "?") if isinstance(result, dict) else "?"
            print(f"OK → {node_id}")
            success += 1
    except Exception as e:
        print(f"FAIL: {e}")
        fail += 1

    time.sleep(0.5)

bridge.close()
print(f"\nDone: {success} succeeded, {fail} failed")
