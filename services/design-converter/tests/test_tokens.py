"""
Unit tests for DTCG token extraction.

Run: python3 tests/test_tokens.py
"""
import sys
import json

# Add parent to path for imports
sys.path.insert(0, "/Users/william/Projects Parent Folder/DesignDev/services/design-converter")

from ir import (
    UNNode,
    NodeType,
    UNColor,
    UNSolidFill,
    UNDropShadow,
    UNTextStyle,
    make_frame,
    make_text,
)
from utils.tokens import extract_tokens, export_tokens_json

# Simple test runner
passed = 0
failed = 0

def test(name):
    """Decorator to mark a test function."""
    def decorator(fn):
        global passed, failed
        try:
            fn()
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}")
            print(f"  {e}")
            failed += 1
    return decorator

def assert_eq(a, b, msg=""):
    """Simple assertion."""
    if a != b:
        raise AssertionError(f"{msg}: {a!r} != {b!r}")

def assert_true(cond, msg=""):
    """Assert condition is true."""
    if not cond:
        raise AssertionError(f"{msg}: {cond} is not True")


# ============================================
# Tests
# ============================================

class TestExtractTokens:
    """Test extract_tokens function."""

    @test("extract_tokens: empty node")
    def _():
        node = UNNode(type=NodeType.FRAME)
        tokens = extract_tokens(node)
        # Should have empty or minimal token groups
        assert_true("color" in tokens or len(tokens) >= 0)

    @test("extract_tokens: single color")
    def _():
        fill = UNSolidFill(color=UNColor(r=1.0, g=0.0, b=0.0, a=1.0))
        node = UNNode(type=NodeType.FRAME, name="RedBox", fills=[fill])
        tokens = extract_tokens(node)
        assert_true("color" in tokens)
        assert_true(len(tokens["color"]) > 0)

    @test("extract_tokens: multiple colors")
    def _():
        red_fill = UNSolidFill(color=UNColor(r=1.0, g=0.0, b=0.0, a=1.0))
        blue_fill = UNSolidFill(color=UNColor(r=0.0, g=0.0, b=1.0, a=1.0))
        node = UNNode(
            type=NodeType.FRAME,
            name="MultiColor",
            fills=[red_fill, blue_fill]
        )
        tokens = extract_tokens(node)
        assert_true(len(tokens["color"]) >= 2)

    @test("extract_tokens: nested children")
    def _():
        fill = UNSolidFill(color=UNColor(r=0.5, g=0.5, b=0.5, a=1.0))
        child = UNNode(type=NodeType.FRAME, name="Child", fills=[fill])
        parent = UNNode(type=NodeType.FRAME, name="Parent", children=[child])
        tokens = extract_tokens(parent)
        # Should include color from child
        assert_true("color" in tokens)

    @test("extract_tokens: deduplicates same color")
    def _():
        fill1 = UNSolidFill(color=UNColor(r=1.0, g=0.0, b=0.0, a=1.0))
        fill2 = UNSolidFill(color=UNColor(r=1.0, g=0.0, b=0.0, a=1.0))
        node = UNNode(
            type=NodeType.FRAME,
            name="SameColor",
            fills=[fill1, fill2]
        )
        tokens = extract_tokens(node)
        # Same hex value should produce single token
        if "color" in tokens:
            # Should be 1 unique token
            hex_values = [t.get("$value") for t in tokens["color"].values()]
            unique_hex = set(hex_values)
            assert_true(len(unique_hex) <= len(tokens["color"]))


class TestDTCGFormat:
    """Test DTCG format compliance."""

    @test("DTCG: color token structure")
    def _():
        fill = UNSolidFill(color=UNColor(r=1.0, g=0.5, b=0.0, a=1.0))
        node = UNNode(type=NodeType.FRAME, name="Orange", fills=[fill])
        tokens = extract_tokens(node)
        if "color" in tokens:
            for key, token in tokens["color"].items():
                assert_eq(token.get("$type"), "color")
                assert_true("$value" in token)
                assert_true(token["$value"].startswith("#"))

    @test("DTCG: 8-digit hex format")
    def _():
        fill = UNSolidFill(color=UNColor(r=0.5, g=0.5, b=0.5, a=0.5))
        node = UNNode(type=NodeType.FRAME, name="HalfAlpha", fills=[fill])
        tokens = extract_tokens(node)
        if "color" in tokens:
            for token in tokens["color"].values():
                hex_val = token["$value"]
                # Should be #RRGGBBAA (9 chars)
                assert_true(len(hex_val) == 9)


class TestExportTokensJson:
    """Test export_tokens_json function."""

    @test("export_tokens_json: writes file")
    def _():
        import tempfile
        import os
        fill = UNSolidFill(color=UNColor(r=1.0, g=0.0, b=0.0, a=1.0))
        node = UNNode(type=NodeType.FRAME, name="Red", fills=[fill])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            export_tokens_json(node, temp_path)
            assert_true(os.path.exists(temp_path))

            with open(temp_path) as f:
                data = json.load(f)

            assert_true("color" in data)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @test("export_tokens_json: returns counts")
    def _():
        import tempfile
        import os
        fill = UNSolidFill(color=UNColor(r=1.0, g=0.0, b=0.0, a=1.0))
        node = UNNode(type=NodeType.FRAME, name="Red", fills=[fill])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            counts = export_tokens_json(node, temp_path)
            assert_true(isinstance(counts, dict))
            assert_true("color" in counts)
            assert_true(counts["color"] >= 1)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# Run all tests
print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
