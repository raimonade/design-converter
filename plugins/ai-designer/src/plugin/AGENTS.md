# Plugin Sandbox Code

**Purpose**: Figma plugin sandbox with AI-powered design generation.

## STRUCTURE
```
src/plugin/
├── code.ts              # Message handler - UI↔sandbox bridge
├── system-prompt.ts     # 578 lines of AI design rules + UI-UX-Pro-Max integration
├── design-generator.ts  # Frame/component/token creation
├── phase-orchestrator.ts # Tool-based execution phases
├── tool-executor.ts     # Individual tool operations
└── tool-schema.ts       # Tool definitions
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Message routing | `code.ts:15-44` | switch/case for all UI messages |
| AI model configs | `code.ts:115-133` | glm/kimi/minimax endpoints |
| JSON extraction | `code.ts:206-222` | Brace-matching parser |
| **UI Style guidance** | `system-prompt.ts:94-144` | Glassmorphism, Claymorphism, etc. |
| **Industry guidance** | `system-prompt.ts:146-225` | Banking, Healthcare, SaaS, etc. |
| **Typography pairings** | `system-prompt.ts:227-248` | Professional, Elegant, Friendly, etc. |
| **UX Quality Rules** | `system-prompt.ts:250-280` | Accessibility, Layout, Performance |
| **Anti-patterns** | `system-prompt.ts:282-310` | Critical, Figma-specific, Industry |
| Variable binding | `design-generator.ts:84-97` | semanticVariables map |
| Fill → boundVariables | `design-generator.ts:174-197` | `VARIABLE_ALIAS` pattern |
| Page organization | `design-generator.ts:115-133` | Atoms/Molecules/Organisms |

## CONVENTIONS
- **Target**: ES2017 (Figma sandbox limit)
- **Output**: IIFE via Vite (`vite.config.plugin.ts`)
- **Fonts**: Inter (Regular/Medium/Bold) - loaded async
- **Colors**: 0-1 range (NOT 0-255)

## DESIGN INTELLIGENCE (UI-UX-Pro-Max Integration)

The system-prompt.ts now includes design intelligence from UI-UX-Pro-Max:

### UI Styles Available
- **Glassmorphism** - Frosted glass, modern SaaS
- **Claymorphism** - Soft 3D, educational apps
- **Minimalism** - Clean whitespace, enterprise
- **Neumorphism** - Soft shadows, wellness apps
- **Brutalism** - Bold, artistic projects
- **Bento Box Grid** - Card layouts, dashboards
- **Dark Mode** - Gaming, entertainment
- **Soft UI Evolution** - Premium, lifestyle brands

### Industry-Specific Rules
| Industry | Primary Color | Style | Typography |
|----------|---------------|-------|------------|
| Banking | Blue #0080FF | Minimalism | Professional |
| Healthcare | Teal #14B8A6 | Soft UI | Clean |
| SaaS | Blue #2563EB | Glassmorphism | Modern |
| E-commerce | Orange #F97316 | Soft UI | Friendly |
| Educational | Yellow #EAB308 | Claymorphism | Friendly |
| Gaming | Purple #8B5CF6 | Dark Mode | Bold |
| Beauty | Pink #E8B4B8 | Soft UI | Elegant |

### UX Quality Requirements
- Touch targets: 44x44px minimum
- Color contrast: 4.5:1 minimum
- Transitions: 150-300ms
- Focus states: Visible on all interactive elements

## ANTI-PATTERNS (THIS FOLDER)
- **NEVER** use `color` directly in fills → use `semanticColor` + `findVariable()`
- **NEVER** hardcode RGB values in generated specs
- **ALWAYS** call `loadFontAsync()` before creating text
- **ALWAYS** validate `primaryAxisSizingMode` is "AUTO" or "FIXED"
- **NEVER** use emojis as UI icons
- **NEVER** create glass elements with bg-white/10 in light mode

## KEY PATTERNS

### Semantic Variable Binding
```typescript
// design-generator.ts:180-188
if (fill.semanticColor) {
  const variable = findVariable(fill.semanticColor);
  return {
    type: "SOLID",
    color: { r: 0, g: 0, b: 0 },  // Placeholder
    boundVariables: { color: { type: "VARIABLE_ALIAS", id: variable.id } }
  };
}
```

### Message Handler Pattern
```typescript
// code.ts:12-44
figma.ui.onmessage = async (message) => {
  switch (message.type) {
    case "generate-design": await handleGenerateDesign(message); break;
    case "load-keys": await handleLoadKeys(); break;
    // ...
  }
};
```

## NOTES
- No direct DOM access (sandbox isolation)
- Network requests allowed via manifest.json whitelist
- `figma.clientStorage` for API key persistence
- UI-UX-Pro-Max skill available at `~/.config/opencode/skill/ui-ux-pro-max/` for extended research
