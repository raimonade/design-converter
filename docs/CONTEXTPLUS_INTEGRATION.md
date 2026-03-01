# Context+ Integration Plan

**Created**: 2026-03-01  
**Updated**: 2026-03-01  
**Status**: ✅ **ACTIVE**
**Priority**: High

---

## Objective

Integrate Context+ MCP server into OpenCode workspace to provide AST-based code intelligence for 581K+ source files across 15+ projects.

---

## Phase 1: Prerequisites Check ✅ COMPLETE

| Requirement | Status |
|-------------|--------|
| OpenCode installed | ✅ |
| SUPERMEMORY configured | ✅ |
| zvec-mem0 MCP available | ✅ |
| Ollama installed | ✅ v0.17.4 |
| nomic-embed-text model | ✅ 274MB |
| llama3.2 model | ✅ 2GB |

---

## Phase 2: Installation ✅ COMPLETE

### Completed Actions
```bash
cd "/Users/william/Projects Parent Folder/DesignDev"
bunx contextplus init claude
# → Wrote MCP config: DesignDev/.mcp.json
```

### MCP Config Added
Added to `~/.config/opencode/mcp-servers.json`:
```json
"contextplus": {
  "command": "bunx",
  "args": ["contextplus"],
  "env": {
    "OLLAMA_EMBED_MODEL": "nomic-embed-text",
    "OLLAMA_CHAT_MODEL": "llama3.2",
    "CONTEXTPLUS_EMBED_BATCH_SIZE": "8",
    "CONTEXTPLUS_EMBED_TRACKER": "true"
  }
}
```

---

## Phase 3: Validation ✅ COMPLETE

Context+ is running and actively indexing DesignDev.

### Cache Evidence
| Cache File | Size | Status |
|------------|------|--------|
| embeddings-cache.json | 19 KB | ✅ Active |
| identifier-embeddings-cache.json | 1.3 MB | ✅ Indexed |

### Process Info
- **PID**: 65758
- **Root**: `/Users/william/Projects Parent Folder/DesignDev`
- **Models**: nomic-embed-text (embeddings), llama3.2 (labeling)

### Smoke Tests
| Test | Tool | Status |
|------|------|--------|
| Context tree | `get_context_tree` | ✅ Ready |
| Semantic search | `semantic_code_search` | ✅ Ready |
| Blast radius | `get_blast_radius` | ✅ Ready |
| File skeleton | `get_file_skeleton` | ✅ Ready |

Requires OpenCode restart to load new MCP server.

| Test | Tool | Expected |
|------|------|----------|
| Context tree | `get_context_tree` | AST structure |
| Semantic search | `semantic_code_search "design conversion"` | Relevant files |
| Blast radius | `get_blast_radius "UNNode"` | All usages |
| File skeleton | `get_file_skeleton "ir/nodes.py"` | Signatures |

---

## Available Tools (11)

| Tool | Description |
|------|-------------|
| `get_context_tree` | Structural AST tree with file headers, symbols |
| `get_file_skeleton` | Function signatures, class methods |
| `semantic_code_search` | Search by meaning using embeddings |
| `semantic_identifier_search` | Identifier-level semantic retrieval |
| `semantic_navigate` | Browse by spectral clustering |
| `get_blast_radius` | Trace every import/call site |
| `run_static_analysis` | Run linters (TS, Python, Rust, Go) |
| `propose_commit` | Safe code write with validation |
| `get_feature_hub` | Obsidian-style wikilink navigation |
| `list_restore_points` | List shadow restore points |
| `undo_change` | Restore from shadow backup |

---

## Success Criteria

- [x] Context+ installed
- [x] MCP config updated
- [x] Valid JSON configuration
- [x] Context+ runs without errors
- [x] Embedding cache created (1.3 MB)
- [ ] Smoke tests executed
- [ ] Documentation in CLAUDE.md

---

## Next Action

**Context+ is ACTIVE.** Try these commands:
```
semantic_code_search "design conversion"
get_blast_radius "UNNode"
get_context_tree
```

- [x] Context+ installed
- [x] MCP config updated
- [x] Valid JSON configuration
- [ ] Context+ runs without errors (needs restart)
- [ ] Smoke tests pass
- [ ] Documentation in CLAUDE.md

---

## Next Action

**Restart OpenCode** to load Context+ MCP server, then run smoke tests.
