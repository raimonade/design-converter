# `ptf` legacy direct converter

`ptf` supports the current working `paper_to_figma.py` CLI.

Flow:

```text
Paper MCP → TreeNode → Figma Plugin API JavaScript → Figma bridge
```

This package is intentionally kept separate from the canonical `design_converter/` package. New conversion behavior should prefer the `UNNode` seam in `design_converter/ir/` unless it is specifically fixing the legacy direct path.
