# LLM Knowledge Base

**Purpose**: AI design generation guidelines and patterns.

## STRUCTURE
```
docs/knowledge/
├── LLM-GENERATION-GUIDELINES.md  # Critical rules for AI output
├── TEXT-COMPONENTS.md            # Text atom patterns
├── DESIGN-SYSTEM-PATTERNS.md     # Component composition
└── TOKEN-COMPONENT-MAPPING.md    # Token→component relationships
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Generation rules | `LLM-GENERATION-GUIDELINES.md` | NEVER/ALWAYS patterns |
| Text components | `TEXT-COMPONENTS.md` | Do/Don't lists |
| Atomic structure | `DESIGN-SYSTEM-PATTERNS.md` | atom/molecule/organism |
| Token mapping | `TOKEN-COMPONENT-MAPPING.md` | Variable bindings |

## KEY GUIDELINES

### Token Creation (First)
1. Create primitive tokens (colors, spacing, radius)
2. Create semantic tokens (background, foreground, primary, etc.)
3. Reference semantics, never primitives directly

### Component Hierarchy
- `atom/` — button, input, badge, avatar, label, checkbox
- `molecule/` — form-field, card, list-item, toast
- `organism/` — header, sidebar, login-form, modal

### Naming Convention
```
{prefix}/{component-name}
Examples: atom/button, molecule/form-field, organism/login-form
```

## ANTI-PATTERNS (THIS FOLDER)
- **NEVER** hardcode hex values or font sizes
- **NEVER** use fixed dimensions on main frames → use `HUG`
- **NEVER** create inline duplicates → use refs
- **NEVER** skip line height on text
- **NEVER** clip frame children → `clip: false`
- **ALWAYS** create tokens before components
- **ALWAYS** create Text components before other atoms

## OUTPUT FORMAT
AI must generate JSON with:
```json
{
  "semantics": { "semantics": { "colors": {...}, "spacing": {...} } },
  "root": { "type": "FRAME", "name": "atom/button", ... }
}
```

## NOTES
- These docs inform `system-prompt.ts` AI rules
- Semantic tokens → Figma variables via `createSemanticVariableCollection()`
- Colors in 0-1 range, spacing multiples of 4
