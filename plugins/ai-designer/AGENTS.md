# Figma AI Designer

**Purpose**: Open-source AI-powered Figma design generator with multi-model support (GLM-5, Kimi).

## STRUCTURE
```
figma-ai-designer/
├── src/plugin/           # Figma sandbox code (IIFE, ES2017)
│   ├── code.ts           # Main plugin entry - message handling
│   ├── system-prompt.ts  # AI prompts + design rules (578 lines, UI-UX-Pro-Max integrated)
│   └── design-generator.ts # Frame/component creation
├── src/ui/               # Preact UI (separate bundle)
│   ├── App.tsx           # UI root
│   ├── components/       # Preact components
│   └── services/         # AI service layer
├── proxy/server.js       # LLM proxy (port 11435)
├── service-manager/      # Service orchestrator (port 11436)
└── tokens/               # Design token exports (css/json/tailwind)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Plugin message handling | `src/plugin/code.ts` | UI↔sandbox bridge |
| **UI Style guidance** | `src/plugin/system-prompt.ts:94-144` | Glassmorphism, Claymorphism, etc. |
| **Industry guidance** | `src/plugin/system-prompt.ts:146-225` | Banking, Healthcare, SaaS, etc. |
| **Typography pairings** | `src/plugin/system-prompt.ts:227-248` | Professional, Elegant, Friendly |
| **UX Quality rules** | `src/plugin/system-prompt.ts:250-280` | Accessibility, Performance |
| **Anti-patterns** | `src/plugin/system-prompt.ts:282-310` | Critical, Figma-specific, Industry |
| Component creation | `src/plugin/design-generator.ts` | Frame→Component logic |
| UI state | `src/ui/App.tsx` | Preact hooks |
| Token bindings | `src/plugin/design-generator.ts:84-97` | semanticVariables map |
| LLM knowledge | `docs/knowledge/` | LLM-GENERATION-GUIDELINES.md |

## CONVENTIONS
- **Build**: Dual Vite (plugin IIFE + UI singlefile)
- **UI**: Preact + Tailwind v4 via `@tailwindcss/vite`
- **Target**: ES2017 (Figma sandbox constraint)
- **AI**: Z.AI Coding Plan (`open.bigmodel.cn`)
- **Naming**: Atomic design prefixes (`atom/`, `molecule/`, `organism/`)

## DESIGN INTELLIGENCE (v2.0)

The system now integrates UI-UX-Pro-Max design intelligence:

### Supported UI Styles
| Style | Best For | Key Properties |
|-------|----------|----------------|
| Glassmorphism | Modern SaaS, Finance | bg-white/80, blur 12-20px |
| Claymorphism | Educational, Children | Soft 3D, 16-24px radius |
| Minimalism | Enterprise, Documentation | Whitespace, 2-3 colors |
| Neumorphism | Wellness, Meditation | Soft shadows, mono palette |
| Brutalism | Portfolios, Art | Bold type, high contrast |
| Bento Grid | Dashboards, Products | Card layout, varied sizes |
| Dark Mode | Gaming, Entertainment | #0F172A bg, #F9FAFB text |
| Soft UI Evolution | Beauty, Lifestyle | Soft shadows, premium feel |

### Industry Color Defaults
| Industry | Primary | CTA | Avoid |
|----------|---------|-----|-------|
| Banking | #0080FF | Blue | AI gradients |
| Healthcare | #14B8A6 | Teal | Dark mode |
| SaaS | #2563EB | Purple | - |
| E-commerce | #F97316 | Pink | Neumorphism |
| Beauty | #E8B4B8 | Gold | Dark mode |

## ANTI-PATTERNS (THIS PROJECT)
- **NEVER** use `color` property in fills/strokes - use `semanticColor`
- **NEVER** use hardcoded hex values - bind to semantic tokens
- **NEVER** create monolithic components - break into atoms + molecules
- **NEVER** forget `primaryAxisSizingMode: "AUTO"` for hug contents
- **NEVER** use emojis as UI icons - use SVG or text labels
- **ALWAYS** prefix component names: `atom/button`, `molecule/form-field`
- **ALWAYS** create semantic variables before components
- **ALWAYS** ensure touch targets 44x44px minimum
- **ALWAYS** maintain 4.5:1 color contrast ratio

## COMMANDS
```bash
npm run dev          # Concurrent: plugin watch + UI dev server
npm run build        # Production build → dist/code.js + dist/ui.js
npm run proxy        # Start LLM proxy (port 11435)
npm run services     # Start service manager (port 11436)
npm run test         # Run tests/test-plugin.js
```

## KEY INTERFACES
```typescript
// Design spec from AI (src/plugin/design-generator.ts)
interface DesignSpec {
  version: string;
  tokens?: Record<string, Record<string, unknown>>;
  semantics?: { semantics: { colors: {...}, spacing: {...} } };
  root: FrameSpec | ComponentVariantSpec;
}

// Fill with variable binding (design-generator.ts:174-197)
interface FillSpec {
  type: string;
  semanticColor?: string;  // → boundVariables: { color: VARIABLE_ALIAS }
  color?: ColorSpec;       // Fallback if no variable
}
```

## ARCHITECTURE NOTES
- **3 independent processes**: Plugin sandbox, proxy server, service manager
- **CORS workaround**: Kimi/Minimax routed through service manager
- **Variable binding**: `findVariable()` → `boundVariables: { color: VARIABLE_ALIAS }`
- **Page organization**: Atoms/Molecules/Organisms pages created dynamically
- **UI-UX-Pro-Max**: Skill at `~/.config/opencode/skill/ui-ux-pro-max/` for extended design research
