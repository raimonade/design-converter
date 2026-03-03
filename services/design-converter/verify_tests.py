#!/usr/bin/env python3
"""
Simple verification script to test design-converter modules without pytest.
Tests imports and basic functionality.
"""
import sys
from pathlib import Path

# Add service root to path
svc_root = Path(__file__).parent
sys.path.insert(0, str(svc_root))

errors = []
passed = 0

# Test 1: Import core IR modules
print("Test 1: Import IR modules...")
try:
    from ir import (
        NodeType, LayoutMode, JustifyContent, AlignItems,
        UNColor, UNSize, UNPadding, UNCornerRadius, UNNode, UNTextStyle,
        make_frame, make_text, un_node_to_dict
    )
    print("  OK IR modules imported successfully")
    passed += 1
except Exception as e:
    errors.append(f"IR import failed: {e}")
    print(f"  FAIL IR import failed: {e}")

# Test 2: Import bridge server
print("Test 2: Import bridge server...")
try:
    from adapters.figma.bridge_server import FigmaBridgeServer, DEFAULT_PORT
    print(f"  OK Bridge server imported (DEFAULT_PORT={DEFAULT_PORT})")
    passed += 1
except Exception as e:
    errors.append(f"Bridge server import failed: {e}")
    print(f"  FAIL Bridge server import failed: {e}")

# Test 3: Test UNNode creation
print("Test 3: Create UNNode...")
try:
    node = UNNode(
        id="test:1",
        name="TestNode",
        type=NodeType.FRAME,
        x=0, y=0, width=100, height=100
    )
    assert node.id == "test:1"
    assert node.type == NodeType.FRAME
    print("  OK UNNode creation works")
    passed += 1
except Exception as e:
    errors.append(f"UNNode creation failed: {e}")
    print(f"  FAIL UNNode creation failed: {e}")

# Test 4: Test UNNode serialization (via un_node_to_dict)
print("Test 4: Test UNNode serialization...")
try:
    node = UNNode(
        id="test:2",
        name="SerializeTest",
        type=NodeType.TEXT,
        x=10, y=20, width=200, height=30,
        text_content="Hello World"
    )
    data = un_node_to_dict(node)
    assert data["id"] == "test:2"
    assert data["type"] == "TEXT"
    assert data["text_content"] == "Hello World"
    print("  OK UNNode serialization works")
    passed += 1
except Exception as e:
    errors.append(f"UNNode serialization failed: {e}")
    print(f"  FAIL UNNode serialization failed: {e}")

# Test 5: Test bridge server config
print("Test 5: Test bridge server config...")
try:
    from adapters.figma.bridge_server import DEFAULT_PORT
    assert DEFAULT_PORT == 9223, f"Expected DEFAULT_PORT=9223, got {DEFAULT_PORT}"
    print(f"  OK Bridge server config correct (port={DEFAULT_PORT})")
    passed += 1
except Exception as e:
    errors.append(f"Bridge server config failed: {e}")
    print(f"  FAIL Bridge server config failed: {e}")

# Test 6: Test FigmaWriter import
print("Test 6: Test FigmaWriter import...")
try:
    from adapters.figma.writer import FigmaWriter
    print("  OK FigmaWriter imported")
    passed += 1
except Exception as e:
    errors.append(f"FigmaWriter import failed: {e}")
    print(f"  FAIL FigmaWriter import failed: {e}")

# Test 7: Test converter module
print("Test 7: Test converter module...")
try:
    from converter import DesignConverter, ConvertSpec
    print("  OK Converter module imported")
    passed += 1
except Exception as e:
    errors.append(f"Converter import failed: {e}")
    print(f"  FAIL Converter import failed: {e}")

# Test 8: Test make_frame factory (correct API)
print("Test 8: Test make_frame factory...")
try:
    frame = make_frame(name="FactoryFrame", width=200, height=150)
    assert frame.name == "FactoryFrame"
    assert frame.type == NodeType.FRAME
    print("  OK make_frame factory works")
    passed += 1
except Exception as e:
    errors.append(f"make_frame factory failed: {e}")
    print(f"  FAIL make_frame factory failed: {e}")

# Test 9: Test make_text factory
print("Test 9: Test make_text factory...")
try:
    text = make_text(name="FactoryText", width=100, height=30)
    assert text.name == "FactoryText"
    assert text.type == NodeType.TEXT
    print("  OK make_text factory works")
    passed += 1
except Exception as e:
    errors.append(f"make_text factory failed: {e}")
    print(f"  FAIL make_text factory failed: {e}")

# Summary
print("")
print("=" * 50)
print(f"Results: {passed}/9 tests passed")
if errors:
    print("")
    print("Errors:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("All verification tests passed!")
    sys.exit(0)
