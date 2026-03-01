# Dashboard Improvements Roadmap

## Source Files Reference
- `services/design-converter/docs/UNNODE_DEEP_DIVE.html` (855 lines, 9 sections)
- `dashboards/figma-tools.html` (MCP servers, CLI tools, IR Reference)

---

## 1. Missing Content from UNNODE_DEEP_DIVE.html

### §3 Figma REST API
**Status:** ❌ Not implemented

Missing content:
- Authentication methods (Personal Access Token, OAuth)
- Rate limits (45 req/min unauthenticated, varies for authenticated)
- Field mapping table (Figma API → UNNode fields)
- Example API responses
- Error handling patterns

**Action:** Add `/figma-api` page or section in IR Reference

---

### §4 Competitive Landscape
**Status:** ❌ Not implemented

Missing competitors:
| Tool | Description |
|------|-------------|
| Octopus (opendesigndev) | Figma + Sketch + XD + Adobe IR |
| html-to-figma | HTML/CSS → Figma Plugin API |
| figma-to-code | Figma → React/Vue/HTML export |
| Figma REST API | Direct API access (read-only for most) |

**Action:** Add competitive analysis section to Dashboard or new page

---

### §5 Feature Matrix
**Status:** ❌ Not implemented

Missing coverage matrix:
| Feature | Figma | Paper | Pencil |
|---------|:-----:|:-----:|:------:|
| Frame/Rectangle | ✅ | ✅ | ✅ |
| Text with runs | ✅ | ✅ | ⚠️ |
| Auto Layout | ✅ | ✅ | ❌ |
| Components | ✅ | ⚠️ | ❌ |
| Variables | ✅ | ❌ | ✅ |
| Gradients | ✅ | ⚠️ | ✅ |
| Effects (shadows) | ✅ | ✅ | ⚠️ |
| Images | ✅ | ✅ | ✅ |
| Vector paths | ⚠️ | ❌ | ✅ |

**Action:** Add feature matrix table to IR Reference or Dashboard

---

### §6 Gap Analysis
**Status:** ⚠️ Component created but not used

`GapCard.tsx` exists but not integrated. Missing gaps:

| ID | Title | Severity |
|----|-------|----------|
| G1 | Component overrides | Critical |
| G2 | Mask nodes (isMask) | Important |
| G3 | Stroke dashes + line caps | Important |
| G4 | Blend mode per fill | Nice |
| G5 | Grid layout mode | Nice |
| G6 | Variable scoping | Important |

**Action:** Add Gap Analysis section to IR Reference using GapCard component

---

### §7 Roadmap / Phase Timeline
**Status:** ⚠️ Component created but not used

`PhaseCard.tsx` exists but not integrated. Missing phases:

| Phase | Status | Items |
|-------|--------|-------|
| Phase 1 | ✅ Done | Core IR, Figma reader/writer |
| Phase 2 | ✅ Done | Paper adapter, rich text runs |
| Phase 3 | ✅ Done | Pencil adapter, DTCG tokens |
| Phase 4 | 🔜 Next | Component overrides, mask nodes |
| Phase 5 | 📋 Future | Grid layout, vector boolean ops |

**Action:** Add Roadmap section to Dashboard using PhaseCard component

---

### §8 Implementation Guide
**Status:** ⚠️ Partially done

Dashboard has Quick Start section but missing:
- Detailed CLI flag reference (`--dry-run`, `--json`, `--list`, `--info`)
- HTTP bridge mode setup instructions
- Desktop Bridge plugin installation
- MCP connection debugging
- Error codes reference (exit codes 0, 1, 2)

**Action:** Expand Quick Start or add dedicated Implementation page

---

### §9 Appendices
**Status:** ⚠️ Partially done

Enum reference exists but missing:
- Changelog table (version history)
- UNColor helper methods reference
- Factory functions reference (`make_frame`, `make_text`, `make_rect`)
- Serialisation format specification

**Action:** Add Appendices section to IR Reference

---

## 2. Missing from figma-tools.html

### MCP Server Details
**Status:** ⚠️ Partially done

Dashboard shows MCP servers but missing:
- Connection status (live indicator)
- Protocol details (WebSocket port, SSE endpoint)
- Tool count per server (shown but not clickable)
- Individual tool documentation

**Action:** Add `/tools/:serverId` detail page or expand Tools page

---

### CLI Tools Reference
**Status:** ❌ Not implemented

Tools page exists but needs:
- Full list of CLI tools with descriptions
- Usage examples for each tool
- Input/output specifications
- Error handling guides

**Action:** Expand `/tools` page with full CLI reference

---

## 3. Technical Improvements

### Performance
- [ ] Add lazy loading for IR sections
- [ ] Implement section scroll spy for active nav highlighting
- [ ] Add search/filter for enums and fields

### Accessibility
- [ ] Add ARIA labels to navigation
- [ ] Keyboard navigation for sidebar
- [ ] Skip-to-content link

### Mobile
- [ ] Hamburger menu for sidebar
- [ ] Responsive tables (horizontal scroll or card view)
- [ ] Touch-friendly code block scrolling

### SEO
- [ ] Add meta descriptions per page
- [ ] Structured data for documentation
- [ ] Sitemap generation

---

## 4. Content Accuracy Verification

### Data to Verify Against Actual Codebase
- [ ] MCP server tool counts match actual `mcp-config.json`
- [ ] IR dataclass count (currently says 15) matches `ir/nodes.py`
- [ ] Enum count (currently says 13) matches actual enums
- [ ] Lines of code metrics are current
- [ ] Adapter line counts are current

### Content to Add from nodes.py
- [ ] `UNCornerRadius` fields
- [ ] `UNPadding` fields
- [ ] `UNGradientStop` structure
- [ ] `UNTextRun` validation rules
- [ ] `UNVariableBinding` fields

---

## 5. New Pages to Create

| Page | Priority | Description |
|------|----------|-------------|
| `/figma-api` | Medium | Figma REST API reference |
| `/architecture` | Low | Deep dive into 3-layer architecture |
| `/changelog` | Low | Version history from git tags |

---

## 6. Component Improvements

### CodeBlock
- [ ] Add syntax highlighting (highlight.js or shiki)
- [ ] Add line numbers option
- [ ] Add file name display
- [ ] Support multiple languages (bash, python, typescript)

### FieldTable
- [ ] Add "Required" indicator
- [ ] Add "Since version" column
- [ ] Link types to their definitions

### Sidebar
- [ ] Add scroll position persistence
- [ ] Add collapse/expand for sections
- [ ] Add external link indicators

---

## 7. Quick Wins

1. **Fix GitHub link** — Currently goes to `github.com`, should be `github.com/willbnu/DesignDev`
2. **Add copy link to sections** — Click § to copy anchor URL
3. **Add "Back to top" button** — Appears on scroll
4. **Add dark/light toggle** — Store preference in localStorage
5. **Add print styles** — For PDF export of documentation

---

## Priority Order

| Priority | Task | Effort | Status |
|----------|------|--------|--------|
| 🔴 High | Fix GitHub link | 1 min | ✅ Done |
| 🔴 High | Feature matrix table | 30 min | ✅ Done |
| 🔴 High | Gap Analysis section | 30 min | ✅ Done |
| 🟡 Medium | Phase/Roadmap section | 30 min | ✅ Done |
| 🟡 Medium | Expand CLI tools reference | 1 hr | ⏳ Pending |
| 🟡 Medium | Verify data accuracy | 1 hr | ⏳ Pending |
| 🟢 Low | Syntax highlighting | 2 hr | ⏳ Pending |
| 🟢 Low | New pages | 3+ hr | ⏳ Pending |
