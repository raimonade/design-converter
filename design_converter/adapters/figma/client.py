"""
Figma REST API Client
=====================
HTTP client for the Figma REST API v1.

Authentication
--------------
Figma supports two auth methods:
  1. Personal Access Token (PAT) — set FIGMA_API_KEY env var
  2. OAuth2 Bearer token — pass token= to constructor

Reference: https://www.figma.com/developers/api
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIGMA_API_BASE = "https://api.figma.com/v1"
DEFAULT_TIMEOUT = 30  # seconds per request
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # seconds, doubled each retry


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FigmaAuthError(Exception):
    """API key / OAuth token missing or invalid."""


class FigmaRateLimitError(Exception):
    """429 — too many requests."""

    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited; retry after {retry_after}s")


class FigmaNotFoundError(Exception):
    """404 — file or node not found."""


class FigmaAPIError(Exception):
    """Any other non-2xx response from Figma."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Figma API error {status}: {body[:200]}")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FigmaClient:
    """
    Thin wrapper around Figma's REST API v1.

    Usage
    -----
    ::

        client = FigmaClient()                         # reads FIGMA_API_KEY
        client = FigmaClient(token="figd_xxxx...")     # explicit PAT
        client = FigmaClient(token="Bearer oauth...")  # OAuth

        file_data  = client.get_file("ABC123")
        node_data  = client.get_file_nodes("ABC123", ["1:2", "3:4"])
        components = client.get_file_components("ABC123")
        styles     = client.get_file_styles("ABC123")
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._token = token or os.environ.get("FIGMA_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries

        if not self._token:
            raise FigmaAuthError(
                "No Figma API token found. "
                "Set the FIGMA_API_KEY environment variable or pass token= to FigmaClient()."
            )

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._token.startswith("Bearer "):
            h["Authorization"] = self._token
        else:
            h["X-Figma-Token"] = self._token
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = FIGMA_API_BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )

        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(),
            method=method,
        )

        delay = RETRY_BACKOFF
        last_exc: Exception = RuntimeError("unreachable")

        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)

            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")

                if exc.code == 401:
                    raise FigmaAuthError("Invalid or expired Figma API token.")
                if exc.code == 403:
                    raise FigmaAuthError("Access denied — check token scopes.")
                if exc.code == 404:
                    raise FigmaNotFoundError(f"Not found: {path}")
                if exc.code == 429:
                    retry_after = int(exc.headers.get("Retry-After", 30))
                    if attempt < self.max_retries:
                        log.warning(
                            "Figma rate limit hit — sleeping %ds before retry",
                            retry_after,
                        )
                        time.sleep(retry_after)
                        continue
                    raise FigmaRateLimitError(retry_after)
                if exc.code >= 500 and attempt < self.max_retries:
                    last_exc = FigmaAPIError(exc.code, raw)
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise FigmaAPIError(exc.code, raw)

            except OSError as exc:  # network / timeout
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

        raise last_exc

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: Dict[str, Any]) -> Any:
        return self._request("POST", path, body=body)

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    def get_file(
        self,
        file_key: str,
        *,
        version: Optional[str] = None,
        depth: Optional[int] = None,
        geometry: Optional[str] = None,  # "paths"
        plugin_data: Optional[str] = None,
        branch_data: bool = False,
    ) -> Dict[str, Any]:
        """
        GET /files/:file_key

        Returns the full document tree for the given Figma file.

        Parameters
        ----------
        file_key   : The alphanumeric key from the Figma URL.
        depth      : How deep to traverse the tree (default = full).
        geometry   : Pass "paths" to include vector geometry.
        """
        return self._get(
            f"/files/{file_key}",
            params={
                "version": version,
                "depth": depth,
                "geometry": geometry,
                "plugin_data": plugin_data,
                "branch_data": "true" if branch_data else None,
            },
        )

    def get_file_nodes(
        self,
        file_key: str,
        node_ids: List[str],
        *,
        version: Optional[str] = None,
        depth: Optional[int] = None,
        geometry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /files/:file_key/nodes

        Returns a subset of the file for the given node IDs.
        Equivalent to selecting specific frames/layers.
        """
        if not node_ids:
            raise ValueError("node_ids must not be empty")
        return self._get(
            f"/files/{file_key}/nodes",
            params={
                "ids": ",".join(node_ids),
                "version": version,
                "depth": depth,
                "geometry": geometry,
            },
        )

    def get_file_versions(self, file_key: str) -> Dict[str, Any]:
        """GET /files/:file_key/versions — list all saved versions."""
        return self._get(f"/files/{file_key}/versions")

    # ------------------------------------------------------------------
    # Components & Styles
    # ------------------------------------------------------------------

    def get_file_components(self, file_key: str) -> Dict[str, Any]:
        """GET /files/:file_key/components — all published components."""
        return self._get(f"/files/{file_key}/components")

    def get_file_component_sets(self, file_key: str) -> Dict[str, Any]:
        """GET /files/:file_key/component_sets — all component sets."""
        return self._get(f"/files/{file_key}/component_sets")

    def get_file_styles(self, file_key: str) -> Dict[str, Any]:
        """GET /files/:file_key/styles — all published styles."""
        return self._get(f"/files/{file_key}/styles")

    def get_component(self, component_key: str) -> Dict[str, Any]:
        """GET /components/:key — single component by key."""
        return self._get(f"/components/{component_key}")

    def get_style(self, style_key: str) -> Dict[str, Any]:
        """GET /styles/:key — single style by key."""
        return self._get(f"/styles/{style_key}")

    # ------------------------------------------------------------------
    # Variables (Figma Variables API — requires Dev/Org plan)
    # ------------------------------------------------------------------

    def get_local_variables(self, file_key: str) -> Dict[str, Any]:
        """
        GET /files/:file_key/variables/local

        Returns all local variables and variable collections defined
        in the file. Requires Figma Organisation or higher.
        """
        return self._get(f"/files/{file_key}/variables/local")

    def get_published_variables(self, file_key: str) -> Dict[str, Any]:
        """GET /files/:file_key/variables/published — published variables."""
        return self._get(f"/files/{file_key}/variables/published")

    def post_variables(self, file_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /files/:file_key/variables

        Create / update / delete variables in bulk.
        `payload` follows the Figma Variables REST API mutation schema.
        """
        return self._post(f"/files/{file_key}/variables", body=payload)

    # ------------------------------------------------------------------
    # Images (export)
    # ------------------------------------------------------------------

    def get_images(
        self,
        file_key: str,
        node_ids: List[str],
        *,
        scale: float = 1.0,
        format: str = "png",  # "jpg" | "png" | "svg" | "pdf"
        svg_include_id: bool = False,
        svg_simplify_stroke: bool = True,
        use_absolute_bounds: bool = False,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /images/:file_key

        Export one or more nodes as images.

        Returns
        -------
        {"images": {"<node_id>": "<url>", ...}, "err": null}
        """
        if not node_ids:
            raise ValueError("node_ids must not be empty")
        params: Dict[str, Any] = {
            "ids": ",".join(node_ids),
            "scale": scale,
            "format": format,
        }
        if svg_include_id:
            params["svg_include_id"] = "true"
        if not svg_simplify_stroke:
            params["svg_simplify_stroke"] = "false"
        if use_absolute_bounds:
            params["use_absolute_bounds"] = "true"
        if version:
            params["version"] = version
        return self._get(f"/images/{file_key}", params=params)

    def get_image_fills(self, file_key: str) -> Dict[str, Any]:
        """
        GET /files/:file_key/images

        Returns S3 download URLs for all images used as fills in the file.
        """
        return self._get(f"/files/{file_key}/images")

    def download_image(self, url: str) -> bytes:
        """Download an image from a Figma CDN URL and return raw bytes."""
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read()

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def get_comments(self, file_key: str) -> Dict[str, Any]:
        """GET /files/:file_key/comments"""
        return self._get(f"/files/{file_key}/comments")

    def post_comment(
        self,
        file_key: str,
        message: str,
        *,
        node_id: Optional[str] = None,
        client_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /files/:file_key/comments"""
        body: Dict[str, Any] = {"message": message}
        if node_id:
            body["client_meta"] = {"node_id": node_id}
        if client_meta:
            body["client_meta"] = client_meta
        return self._post(f"/files/{file_key}/comments", body=body)

    # ------------------------------------------------------------------
    # Teams & Projects
    # ------------------------------------------------------------------

    def get_team_projects(self, team_id: str) -> Dict[str, Any]:
        """GET /teams/:team_id/projects"""
        return self._get(f"/teams/{team_id}/projects")

    def get_project_files(self, project_id: str) -> Dict[str, Any]:
        """GET /projects/:project_id/files"""
        return self._get(f"/projects/{project_id}/files")

    def get_me(self) -> Dict[str, Any]:
        """GET /me — current user info (useful for verifying auth)."""
        return self._get("/me")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """
        Verify connectivity and token validity.
        Returns True on success, raises FigmaAuthError on bad token.
        """
        self.get_me()
        return True

    def extract_file_key(self, url_or_key: str) -> str:
        """
        Parse a Figma file key from a full URL or return it as-is.

        Examples
        --------
        ::

            client.extract_file_key("https://www.figma.com/design/ABC123xyz/My-File")
            # → "ABC123xyz"
            client.extract_file_key("ABC123xyz")
            # → "ABC123xyz"
        """
        if "figma.com" in url_or_key:
            # URLs like: https://www.figma.com/file/KEY/Name
            #        or: https://www.figma.com/design/KEY/Name
            parts = url_or_key.split("/")
            try:
                idx = next(
                    i for i, p in enumerate(parts) if p in ("file", "design", "proto")
                )
                return parts[idx + 1]
            except (StopIteration, IndexError):
                raise ValueError(f"Cannot extract file key from URL: {url_or_key}")
        return url_or_key

    def walk_nodes(
        self,
        node: Dict[str, Any],
        *,
        types: Optional[List[str]] = None,
    ):
        """
        Generator that depth-first walks a Figma node tree dict,
        optionally filtering by node type (e.g. ["FRAME", "TEXT"]).

        Usage
        -----
        ::

            file_data = client.get_file("ABC123")
            document  = file_data["document"]
            for node in client.walk_nodes(document, types=["TEXT"]):
                print(node["name"], node["characters"])
        """
        if types is None or node.get("type") in types:
            yield node
        for child in node.get("children", []):
            yield from self.walk_nodes(child, types=types)

    def find_node_by_name(
        self,
        root: Dict[str, Any],
        name: str,
        *,
        exact: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Search a Figma node tree dict for the first node matching `name`.

        Parameters
        ----------
        root  : Root Figma node dict (e.g. from get_file()["document"]).
        name  : Name to search for.
        exact : If False, perform a case-insensitive substring match.
        """
        for node in self.walk_nodes(root):
            node_name = node.get("name", "")
            if exact:
                if node_name == name:
                    return node
            else:
                if name.lower() in node_name.lower():
                    return node
        return None

    def collect_colors(self, root: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Walk the node tree and collect all unique solid fill colors.

        Returns
        -------
        List of dicts: {"hex": str, "opacity": float, "node_name": str}
        """
        seen: set = set()
        results: List[Dict[str, Any]] = []

        for node in self.walk_nodes(root):
            for fill in node.get("fills", []):
                if fill.get("type") != "SOLID":
                    continue
                c = fill.get("color", {})
                r = int(round(c.get("r", 0) * 255))
                g = int(round(c.get("g", 0) * 255))
                b = int(round(c.get("b", 0) * 255))
                a = fill.get("opacity", c.get("a", 1.0))
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                key = (hex_color, round(a, 3))
                if key not in seen:
                    seen.add(key)
                    results.append(
                        {
                            "hex": hex_color,
                            "opacity": a,
                            "node_name": node.get("name", ""),
                        }
                    )

        return results

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        masked = self._token[:8] + "..." if len(self._token) > 8 else "***"
        return f"<FigmaClient token={masked}>"
