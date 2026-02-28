# DesignDev - Project Identity

**Purpose:** Unified design development workspace for Figma, Pencil, and Paper design tools.

**Vision:** Single source of truth for all design-related development, automation, and knowledge.

---

## Core Beliefs

1. **Everything should be in one place** - No scattered configs or duplicated knowledge
2. **Design is engineering** - Tools, CLI, MCPs are as important as the designs themselves
3. **Automation first** - If you do it twice, script it
4. **Knowledge compounds** - Every lesson learned should be documented
5. **Integration over isolation** - All tools should work together

---

## What We Build

### Plugins
- **AI Designer** - AI-powered Figma plugin with multi-model support
- **Desktop Bridge** - MCP integration for Figma Console

### Tools
- **CLI** - Token extraction, analysis, workflows
- **MCPs** - Model Context Protocol servers
- **Dashboards** - Status and monitoring

### Knowledge
- **Design patterns** - Component architecture, design systems
- **Integration guides** - LLM generation, variable binding
- **Workflows** - Design-to-code pipelines

---

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────────────────┐
│           DesignDev Tools                     │
├─────────────────────────────────────────────┤
│  CLI (bash)  │  MCPs  │  Skills          │
│  figma-*     │  figma │  ui-ux-pro-max  │
│               │  console │                 │
└─────────────────────────────────────────────┘
    │              │           │
    ▼              ▼           ▼
┌─────────────────────────────────────────────┐
│           Design Outputs                      │
├─────────────────────────────────────────────┤
│  Plugins (Figma) │ Designs (Pencil)        │
│  ai-designer     │ paper designs           │
└─────────────────────────────────────────────┘
```

---

## Supported Tools

| Tool | Purpose | Integration |
|------|---------|-------------|
| Figma | Design source | Plugin + MCP |
| Pencil.dev | Design editor | .pen files |
| Paper | Design system | Tokens |
| Claude | AI generation | MCP + CLI |
| OpenCode | Orchestration | Skills |

---

## Workflows

### Design-to-Code
1. Design in Figma
2. AI Designer generates components
3. Extract tokens via CLI
4. Export to CSS/Tailwind/JSON
5. Integrate into codebase

### Design System Building
1. Define semantic variables in Figma
2. Run `design-system` workflow
3. Export tokens
4. Apply to components

### AI Generation
1. Select model (GLM-5, Kimi, GPT-4o)
2. Write prompt
3. AI Designer creates design
4. Refine in Figma

---

## Anti-Patterns

- **Scattered configs** - All config in this repo
- **Duplicated knowledge** - Single source of truth
- **Manual processes** - Automate everything
- **Isolated tools** - Integrate deeply
- **Forgotten learnings** - Document everything

---

## Success Metrics

- All tools accessible from single CLI
- 100% reproducible workflows
- Zero manual token extraction
- Integrated design-to-code pipeline

---

**Last Updated:** 2026-02-28
**Version:** 1.0.0
