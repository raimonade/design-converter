"""
DesignConverter — Orchestrates conversion between Figma, Paper, and Pencil.

Python API
----------
    from converter import DesignConverter

    conv = DesignConverter()
    result = conv.convert("figma:ABC123", "paper:")
    print(result.output)   # Paper node ID

    # Dry-run (read only)
    result = conv.convert("figma:ABC123", "paper:", dry_run=True)
    print(result.node_count)

    # List nodes in a source
    nodes = conv.list_nodes("paper:")

CLI
---
    python3 converter.py SOURCE DEST [OPTIONS]
    python3 converter.py --list SOURCE
    python3 converter.py --info SOURCE

    # Examples
    python3 converter.py figma:ABC123 paper: --verbose
    python3 converter.py figma:ABC123/1:2 pencil: --dry-run --json
    python3 converter.py paper:TO-0 figma: --figma-writer-mode=script
    python3 converter.py --list figma:ABC123 --json

Spec format
-----------
    figma:FILE_KEY                  whole file
    figma:FILE_KEY/NODE_ID          specific node
    https://www.figma.com/design/…  URL (file key auto-extracted)
    paper:                          first artboard
    paper:NODE_ID                   specific node
    pencil:                         first artboard / active file
    pencil:NODE_ID                  specific node

Exit codes
----------
    0   success
    1   general error (bad args, conversion failure, …)
    2   connection failure (tool not running / not reachable)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# path bootstrap — works whether run directly or imported as a module
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from adapters.base import (
    BaseReader,
    BaseWriter,
    ConnectionError as ToolConnectionError,
    NodeNotFoundError,
    WriteError,
)
from adapters.figma import FigmaClient, FigmaReader, FigmaWriter
from adapters.paper import PaperReader, PaperWriter
from adapters.pencil import PencilReader, PencilWriter
from ir.nodes import UNNode, count_nodes

# ---------------------------------------------------------------------------
# ConvertSpec
# ---------------------------------------------------------------------------

_KNOWN_TOOLS = {"figma", "paper", "pencil"}


@dataclass
class ConvertSpec:
    """Parsed tool + node reference."""

    tool: str       # "figma" | "paper" | "pencil"
    node_id: str = ""
    file_key: str = ""  # Figma-only

    @classmethod
    def parse(cls, raw: str) -> "ConvertSpec":
        """
        Accept:
          figma:FILE_KEY
          figma:FILE_KEY/1:2
          https://www.figma.com/...   (auto-detected)
          paper:
          paper:TO-0
          pencil:
          pencil:frame123
        """
        raw = raw.strip()

        # Auto-detect Figma URLs.
        if raw.startswith("http://") or raw.startswith("https://"):
            if "figma.com" in raw:
                client = FigmaClient.__new__(FigmaClient)
                # extract_file_key is a static-ish method; call on dummy.
                try:
                    file_key = FigmaClient.extract_file_key(None, raw)  # type: ignore[arg-type]
                except Exception:
                    # Fallback: parse URL manually.
                    import re
                    m = re.search(r"/(?:design|file|proto)/([A-Za-z0-9_-]+)", raw)
                    file_key = m.group(1) if m else raw
                return cls(tool="figma", file_key=file_key, node_id="")
            raise ValueError(f"Unrecognised URL (only figma.com URLs supported): {raw!r}")

        # Expect "tool:rest".
        if ":" not in raw:
            raise ValueError(
                f"Invalid spec {raw!r}. Expected format: tool:id  "
                f"(e.g. figma:ABC123  paper:TO-0  pencil:)"
            )

        tool, _, rest = raw.partition(":")
        tool = tool.lower()

        if tool not in _KNOWN_TOOLS:
            raise ValueError(
                f"Unknown tool {tool!r}. Must be one of: {', '.join(sorted(_KNOWN_TOOLS))}"
            )

        if tool == "figma":
            # rest may be  "FILE_KEY"  or  "FILE_KEY/NODE_ID"
            if "/" in rest:
                file_key, _, node_id = rest.partition("/")
            else:
                file_key, node_id = rest, ""
            return cls(tool="figma", file_key=file_key.strip(), node_id=node_id.strip())

        return cls(tool=tool, node_id=rest.strip())

    def __str__(self) -> str:
        if self.tool == "figma":
            base = f"figma:{self.file_key}"
            return f"{base}/{self.node_id}" if self.node_id else base
        return f"{self.tool}:{self.node_id}" if self.node_id else f"{self.tool}:"


# ---------------------------------------------------------------------------
# ConvertResult
# ---------------------------------------------------------------------------

@dataclass
class ConvertResult:
    """Outcome of a single conversion."""

    success: bool
    source_spec: str
    dest_spec: str
    node_name: str = ""
    node_type: str = ""
    node_count: int = 0
    output: str = ""   # file path (script mode) or node ID (live modes)
    error: str = ""
    elapsed_ms: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def print_summary(self, *, json_mode: bool = False, file=None) -> None:
        if file is None:
            file = sys.stdout
        if json_mode:
            print(json.dumps(self.as_dict(), indent=2), file=file)
            return
        status = "\033[0;32m✓ OK\033[0m" if self.success else "\033[0;31m✗ FAIL\033[0m"
        print(f"{status}  {self.source_spec}  →  {self.dest_spec}", file=file)
        if self.node_name:
            print(f"   Node  : {self.node_name} ({self.node_type})", file=file)
        if self.node_count:
            print(f"   Nodes : {self.node_count}", file=file)
        if self.output:
            print(f"   Output: {self.output}", file=file)
        if self.error:
            print(f"   Error : {self.error}", file=file)
        print(f"   Time  : {self.elapsed_ms}ms", file=file)


# ---------------------------------------------------------------------------
# DesignConverter
# ---------------------------------------------------------------------------

class DesignConverter:
    """
    Orchestrates design conversions between Figma, Paper, and Pencil.

    Each conversion:
      1. Parses source/dest specs
      2. Creates and connects a reader
      3. Reads the UNNode tree
      4. Creates and connects a writer
      5. Writes the UNNode tree
      6. Returns a ConvertResult

    Readers and writers are always disconnected even on error.
    """

    def __init__(
        self,
        *,
        figma_token: Optional[str] = None,
        figma_writer_mode: str = "script",
        figma_bridge_port: int = 9224,
        figma_http_bridge_port: int = 9223,
        figma_bridge_timeout: float = 30.0,
        figma_connect_timeout: float = 60.0,
        figma_output_dir: Optional[str] = None,
    ) -> None:
        self._figma_token = figma_token
        self._figma_writer_opts: Dict[str, Any] = {
            "mode": figma_writer_mode,
            "bridge_port": figma_bridge_port,
            "http_bridge_port": figma_http_bridge_port,
            "bridge_timeout": figma_bridge_timeout,
            "connect_timeout": figma_connect_timeout,
            "output_dir": figma_output_dir,
        }

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def convert(
        self,
        source: str,
        dest: str,
        *,
        parent_id: str = "",
        replace_id: str = "",
        dry_run: bool = False,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> ConvertResult:
        """Convert from *source* spec to *dest* spec."""
        t0 = time.time()

        def _progress(msg: str) -> None:
            if on_progress:
                on_progress(msg)

        try:
            src = ConvertSpec.parse(source)
            dst = ConvertSpec.parse(dest)
        except ValueError as exc:
            return ConvertResult(
                success=False,
                source_spec=source,
                dest_spec=dest,
                error=str(exc),
                elapsed_ms=_ms(t0),
            )

        # ── read ──────────────────────────────────────────────────────
        reader = self._make_reader(src)
        unnode: Optional[UNNode] = None
        try:
            _progress(f"Connecting to {src.tool}…")
            reader.connect()
            _progress(f"Reading {src}…")
            unnode = self._do_read(reader, src)
        except (ToolConnectionError, ConnectionRefusedError, OSError) as exc:
            return ConvertResult(
                success=False,
                source_spec=source,
                dest_spec=dest,
                error=f"Connection failed ({src.tool}): {exc}",
                elapsed_ms=_ms(t0),
            )
        except NodeNotFoundError as exc:
            return ConvertResult(
                success=False,
                source_spec=source,
                dest_spec=dest,
                error=str(exc),
                elapsed_ms=_ms(t0),
            )
        except Exception as exc:
            return ConvertResult(
                success=False,
                source_spec=source,
                dest_spec=dest,
                error=f"Read error: {exc}",
                elapsed_ms=_ms(t0),
            )
        finally:
            try:
                reader.disconnect()
            except Exception:
                pass

        node_name = unnode.name or ""
        node_type = (
            unnode.type.value if hasattr(unnode.type, "value") else str(unnode.type)
        )
        n_nodes = count_nodes(unnode)
        _progress(
            f"Read {n_nodes} node(s): {node_name!r} ({node_type})"
        )

        if dry_run:
            _progress("Dry-run: skipping write.")
            return ConvertResult(
                success=True,
                source_spec=source,
                dest_spec=dest,
                node_name=node_name,
                node_type=node_type,
                node_count=n_nodes,
                output="(dry-run)",
                elapsed_ms=_ms(t0),
            )

        # ── write ─────────────────────────────────────────────────────
        writer = self._make_writer(dst)
        try:
            _progress(f"Connecting to {dst.tool}…")
            writer.connect()
            _progress(f"Writing to {dst}…")
            output = self._do_write(writer, unnode, dst, parent_id, replace_id)
        except (ToolConnectionError, ConnectionRefusedError, OSError) as exc:
            return ConvertResult(
                success=False,
                source_spec=source,
                dest_spec=dest,
                node_name=node_name,
                node_type=node_type,
                node_count=n_nodes,
                error=f"Connection failed ({dst.tool}): {exc}",
                elapsed_ms=_ms(t0),
            )
        except WriteError as exc:
            return ConvertResult(
                success=False,
                source_spec=source,
                dest_spec=dest,
                node_name=node_name,
                node_type=node_type,
                node_count=n_nodes,
                error=str(exc),
                elapsed_ms=_ms(t0),
            )
        except Exception as exc:
            return ConvertResult(
                success=False,
                source_spec=source,
                dest_spec=dest,
                node_name=node_name,
                node_type=node_type,
                node_count=n_nodes,
                error=f"Write error: {exc}",
                elapsed_ms=_ms(t0),
            )
        finally:
            try:
                writer.disconnect()
            except Exception:
                pass

        _progress(f"Done → {output}")
        return ConvertResult(
            success=True,
            source_spec=source,
            dest_spec=dest,
            node_name=node_name,
            node_type=node_type,
            node_count=n_nodes,
            output=output,
            elapsed_ms=_ms(t0),
        )

    def read_node(self, source: str) -> UNNode:
        """Read source spec and return the raw UNNode tree (no writing)."""
        spec = ConvertSpec.parse(source)
        reader = self._make_reader(spec)
        try:
            reader.connect()
            return self._do_read(reader, spec)
        finally:
            try:
                reader.disconnect()
            except Exception:
                pass

    def list_nodes(self, source: str) -> List[Dict[str, Any]]:
        """Return list of available nodes in the source tool."""
        spec = ConvertSpec.parse(source)
        reader = self._make_reader(spec)
        try:
            reader.connect()
            nodes = reader.list_nodes()
            if not nodes:
                # Fallback: try get_file_info and wrap it.
                info = reader.get_file_info()
                if info:
                    nodes = [info]
            return nodes
        finally:
            try:
                reader.disconnect()
            except Exception:
                pass

    def get_info(self, source: str) -> Dict[str, Any]:
        """Return file/document info for the source tool."""
        spec = ConvertSpec.parse(source)
        reader = self._make_reader(spec)
        try:
            reader.connect()
            return reader.get_file_info()
        finally:
            try:
                reader.disconnect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _make_reader(self, spec: ConvertSpec) -> BaseReader:
        if spec.tool == "figma":
            return FigmaReader(token=self._figma_token)
        if spec.tool == "paper":
            return PaperReader()
        if spec.tool == "pencil":
            return PencilReader()
        raise ValueError(f"No reader for tool: {spec.tool!r}")

    def _make_writer(self, spec: ConvertSpec) -> BaseWriter:
        if spec.tool == "figma":
            return FigmaWriter(**self._figma_writer_opts)
        if spec.tool == "paper":
            return PaperWriter()
        if spec.tool == "pencil":
            return PencilWriter()
        raise ValueError(f"No writer for tool: {spec.tool!r}")

    def _do_read(self, reader: BaseReader, spec: ConvertSpec) -> UNNode:
        # FigmaReader takes (file_key, node_id) — different from BaseReader contract.
        if spec.tool == "figma":
            return reader.read_node(spec.file_key, spec.node_id)  # type: ignore[call-arg]
        return reader.read_node(spec.node_id)

    def _do_write(
        self,
        writer: BaseWriter,
        node: UNNode,
        spec: ConvertSpec,
        parent_id: str,
        replace_id: str,
    ) -> str:
        return writer.write_node(node, parent_id=parent_id, replace_id=replace_id)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ms(t0: float) -> int:
    return int((time.time() - t0) * 1000)


def _is_connection_error(result: ConvertResult) -> bool:
    err = result.error.lower()
    return any(k in err for k in ("connection failed", "connection refused", "not reachable"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="converter.py",
        description=(
            "Convert designs between Figma, Paper Design, and Pencil.\n\n"
            "Spec format:\n"
            "  figma:FILE_KEY           whole Figma file\n"
            "  figma:FILE_KEY/NODE_ID   specific node\n"
            "  https://www.figma.com/…  Figma URL (auto-detected)\n"
            "  paper:                   first Paper artboard\n"
            "  paper:NODE_ID            specific Paper node\n"
            "  pencil:                  active Pencil file\n"
            "  pencil:NODE_ID           specific Pencil node"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s figma:ABC123 paper:\n"
            "  %(prog)s figma:ABC123/1:2 pencil: --dry-run --verbose\n"
            "  %(prog)s paper:TO-0 figma: --figma-writer-mode=script\n"
            "  %(prog)s --list figma:ABC123 --json\n"
            "  %(prog)s --info paper:\n"
            "\n"
            "Exit codes: 0=ok  1=error  2=connection failure"
        ),
    )

    # Action group.
    action = p.add_mutually_exclusive_group()
    action.add_argument(
        "--list",
        dest="list_mode",
        action="store_true",
        help="List available nodes in SOURCE (no conversion)",
    )
    action.add_argument(
        "--info",
        dest="info_mode",
        action="store_true",
        help="Show file/document info for SOURCE",
    )

    # Positional.
    p.add_argument("source", nargs="?", help="Source spec")
    p.add_argument("dest", nargs="?", help="Destination spec (not required for --list/--info)")

    # Conversion options.
    p.add_argument("--parent-id", default="", metavar="ID",
                   help="Parent node ID in destination")
    p.add_argument("--replace-id", default="", metavar="ID",
                   help="Replace an existing node with this ID")
    p.add_argument("--dry-run", action="store_true",
                   help="Read source only; do not write to destination")

    # Output options.
    p.add_argument("--json", dest="json_mode", action="store_true",
                   help="Machine-readable JSON output")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print progress messages")

    # Figma writer options.
    p.add_argument(
        "--figma-writer-mode",
        choices=["script", "bridge", "http"],
        default="script",
        help="FigmaWriter mode: 'script' saves .js; 'bridge' starts WebSocket; 'http' uses bridge server (default: script)",
    )
    p.add_argument("--bridge-port", type=int, default=9224,
                   help="WebSocket bridge port for bridge mode (default: 9224)")
    p.add_argument("--http-bridge-port", type=int, default=9223,
                   help="HTTP bridge port for http mode (default: 9223)")
    p.add_argument("--figma-token", default=None, metavar="TOKEN",
                   help="Figma API token (overrides FIGMA_API_KEY env var)")
    p.add_argument("--output-dir", default=None, metavar="DIR",
                   help="Output directory for script-mode .js files")

    # Token export option.
    p.add_argument(
        "--export-tokens", default=None, metavar="FILE",
        help="After reading the source, extract DTCG design tokens and write to FILE (.json)",
    )

    return p


def _verbose_printer(enabled: bool):
    """Return an on_progress callback that prints if verbose is enabled."""
    def _print(msg: str) -> None:
        if enabled:
            print(f"\033[0;36m  ›\033[0m {msg}", file=sys.stderr)
    return _print


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Validate: source is always required.
    if not args.source:
        parser.error("SOURCE is required.")

    # --export-tokens alone (no dest) implies --dry-run.
    if args.export_tokens and not args.dest and not args.list_mode and not args.info_mode:
        args.dry_run = True

    # Validate: dest is required unless --list / --info / --dry-run / --export-tokens.
    if (not args.list_mode and not args.info_mode
            and not args.dest
            and not args.dry_run
            and not args.export_tokens):
        parser.error(
            "DEST is required for conversion. "
            "Use --dry-run to read without writing, or --list / --info for inspection."
        )

    conv = DesignConverter(
        figma_token=args.figma_token,
        figma_writer_mode=args.figma_writer_mode,
        figma_bridge_port=args.bridge_port,
        figma_http_bridge_port=args.http_bridge_port,
        figma_output_dir=args.output_dir,
    )

    progress = _verbose_printer(args.verbose)

    # ── --list ────────────────────────────────────────────────────────
    if args.list_mode:
        try:
            progress(f"Listing nodes in {args.source}…")
            nodes = conv.list_nodes(args.source)
        except (ToolConnectionError, ConnectionRefusedError, OSError) as exc:
            _print_error(f"Connection failed: {exc}", json_mode=args.json_mode)
            return 2
        except Exception as exc:
            _print_error(str(exc), json_mode=args.json_mode)
            return 1
        if args.json_mode:
            print(json.dumps({"source": args.source, "nodes": nodes}, indent=2))
        else:
            print(f"Nodes in {args.source}:")
            for n in nodes:
                nid = n.get("id", n.get("node_id", "?"))
                name = n.get("name", n.get("title", ""))
                ntype = n.get("type", "")
                print(f"  {nid:<20}  {name:<30}  {ntype}")
        return 0

    # ── --info ────────────────────────────────────────────────────────
    if args.info_mode:
        try:
            progress(f"Getting info for {args.source}…")
            info = conv.get_info(args.source)
        except (ToolConnectionError, ConnectionRefusedError, OSError) as exc:
            _print_error(f"Connection failed: {exc}", json_mode=args.json_mode)
            return 2
        except Exception as exc:
            _print_error(str(exc), json_mode=args.json_mode)
            return 1
        if args.json_mode:
            print(json.dumps({"source": args.source, "info": info}, indent=2))
        else:
            print(f"Info for {args.source}:")
            for k, v in info.items():
                print(f"  {k:<20}: {v}")
        return 0

    # ── convert ───────────────────────────────────────────────────────
    dest_spec = args.dest or ""
    result = conv.convert(
        args.source,
        dest_spec,
        parent_id=args.parent_id,
        replace_id=args.replace_id,
        dry_run=args.dry_run,
        on_progress=progress,
    )

    result.print_summary(json_mode=args.json_mode)

    # ── --export-tokens ───────────────────────────────────────────────
    if args.export_tokens and result.success:
        from utils.tokens import export_tokens_json
        try:
            progress(f"Reading source for token extraction…")
            un_tree = conv.read_node(args.source)
            counts = export_tokens_json(un_tree, args.export_tokens)
            total = sum(counts.values())
            if args.json_mode:
                print(json.dumps({"tokens_file": args.export_tokens, "counts": counts}))
            else:
                parts = ", ".join(f"{v} {k}" for k, v in counts.items() if v)
                print(f"\033[0;32m[tokens]\033[0m {total} tokens → {args.export_tokens}  ({parts})")
        except Exception as exc:
            _print_error(f"Token export failed: {exc}", json_mode=args.json_mode)
            return 1

    if not result.success:
        if _is_connection_error(result):
            return 2
        return 1
    return 0


def _print_error(msg: str, *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps({"success": False, "error": msg}))
    else:
        print(f"\033[0;31m[ERROR]\033[0m {msg}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
