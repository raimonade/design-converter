# Design Converter

Tools for moving designs between Paper Design and Figma.

The repository currently has two paths:

1. **Legacy direct Paper → Figma path** — `paper_to_figma.py` plus `ptf/`.
   This is the quickest working path for converting Paper artboards into Figma Plugin API JavaScript.
2. **Canonical IR path** — `design_converter/`.
   This is the longer-term architecture: adapters read/write a shared `UNNode` design tree.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Run the Figma bridge

Start the local HTTP/WebSocket bridge, then connect the Desktop Bridge plugin in Figma to port `9223`.

```bash
.venv/bin/python3 -m design_converter.adapters.figma.bridge_server --port 9223
```

## Convert Paper artboards with the legacy direct path

```bash
# Convert a specific artboard and push it through the bridge
.venv/bin/python3 paper_to_figma.py --artboard 1J3-0

# Convert all artboards
.venv/bin/python3 paper_to_figma.py

# Dry run: generate JS without pushing to Figma
.venv/bin/python3 paper_to_figma.py --artboard 1J3-0 --dry-run --output /tmp/hero.js
```

## Repository map

| Path | Purpose |
| --- | --- |
| `design_converter/ir/` | `UNNode` intermediate representation and design primitives. |
| `design_converter/adapters/` | Tool adapters at the read/write seam. Currently Figma and Paper. |
| `design_converter/utils/` | Shared parsing helpers for CSS, JSX, SVG, colors, and tokens. |
| `paper_to_figma.py` | Working legacy Paper → Figma CLI. |
| `ptf/` | Legacy direct converter modules used by `paper_to_figma.py`. |
| `tests/` | Unit and integration tests. |
| `tools/` | Small operational helpers. |
| `docs/` | Current architecture notes plus archived research/planning docs. |

## Development checks

```bash
python3 -m compileall -q paper_to_figma.py ptf design_converter tests tools
python3 -m pytest -q
```

If `pytest` is missing, install the dev dependencies first:

```bash
.venv/bin/pip install -r requirements-dev.txt
```

## Architecture notes

Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the current seams and naming. Historical/planning notes live in `docs/archive/` and may describe adapters or CLIs that do not exist yet.
