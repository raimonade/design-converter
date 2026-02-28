# Plugin UI (Vanilla HTML)

**Purpose**: Figma plugin UI with model selection and prompt input.

## STRUCTURE
```
src/ui/
├── index.html           # ACTIVE UI (1714 lines) - vanilla HTML/CSS/JS
├── AGENTS.md            # This file
└── _preact-archived/    # Archived Preact implementation (NOT used in build)
    ├── README.md        # Instructions for restoration
    ├── App.tsx          # Root component
    ├── main.tsx         # Entry point
    ├── styles.css       # Tailwind CSS
    ├── components/      # UI components
    └── services/        # AI service layer
```

## ACTIVE UI: index.html

The build uses `src/ui/index.html` directly (see `vite.config.ui.ts:15`).

### Structure (1714 lines)
- **CSS (lines 7-978)**: 56 CSS custom properties, component styles
- **HTML (lines 980-1263)**: Semantic structure, 11 preset templates
- **JS (lines 1265-1711)**: IIFE pattern, message passing to sandbox

### Features Implemented
| Feature | Implementation |
|---------|----------------|
| Model Selection | GLM-5 / Kimi / MiniMax M2.5 toggle |
| Services Status | Ollama + Proxy health checks |
| Preset Templates | 11 atomic design templates |
| Keyboard Shortcuts | ⌘+Enter, ⌘+K, ⌘+,, Esc |
| API Key Storage | figma.clientStorage via plugin |
| Error Handling | Retry/Dismiss buttons |

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| CSS Variables | `index.html:7-60` | `--figma-*` design tokens |
| Model Toggle | `index.html:1000-1050` | 3-way grid toggle |
| Services Panel | `index.html:1050-1085` | Collapsible status |
| Preset Templates | `index.html:1086-1129` | 11 dropdown options |
| Message Passing | `index.html:1350-1400` | `parent.postMessage()` |
| State Object | `index.html:1270` | Global state object |

## CONVENTIONS
- **Framework**: Vanilla HTML/CSS/JS (IIFE pattern)
- **Styling**: Inline CSS with `--figma-*` custom properties
- **Build**: Single-file output via `vite-plugin-singlefile`
- **Communication**: `parent.postMessage()` for UI↔sandbox

## ANTI-PATTERNS (THIS FOLDER)
- **DON'T** modify without testing in Figma (CSP constraints)
- **DON'T** use ES6+ features that don't transpile to ES2017
- **DON'T** add external dependencies (must be self-contained)
- **DON'T** forget to update both index.html AND dist after changes

## KEY PATTERNS

### Message to Sandbox
```javascript
// index.html pattern
parent.postMessage(
  { pluginMessage: { type: "generate-design", prompt, mode, requestId } },
  "*"
);
```

### DOM Helper Pattern
```javascript
// Cached element references
const elements = {
  prompt: $(".prompt-textarea"),
  generateBtn: $(".generate-btn"),
  // ...
};
```

## NOTES
- UI bundle separate from plugin code (CSP constraints)
- The `_preact-archived/` folder contains an alternative implementation
- To restore Preact, see `_preact-archived/README.md`
