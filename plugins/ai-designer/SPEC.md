# Design System V1 - Figma AI Designer

## Overview
A production-ready design system built in Figma with variables, components, and proper architecture.

## File Info
- **File**: "Plugin Test" (KsHzgtwa7iQ3HXuVBGoLsL)
- **Version**: V1.0
- **Modes**: Light, Dark

## Variable Collection: Design System V1

### Primitives

#### Colors - Slate Scale
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `primitive/colors/slate-50` | #fafafa | #171717 | Page background |
| `primitive/colors/slate-100` | #f4f4f5 | #262626 | Light borders |
| `primitive/colors/slate-200` | #e4e4e7 | #3f3f46 | Borders |
| `primitive/colors/slate-300` | #d4d4d8 | #52525b | Hover borders |
| `primitive/colors/slate-400` | #a1a1aa | #71717a | Muted text |
| `primitive/colors/slate-500` | #71717a | #71717a | Placeholder |
| `primitive/colors/slate-600` | #52525b | #a1a1aa | Secondary |
| `primitive/colors/slate-700` | #3f3f46 | #d4d4d8 | Body text |
| `primitive/colors/slate-800` | #27272a | #e4e4e7 | Headings |
| `primitive/colors/slate-900` | #18181b | #f4f4f5 | Primary text |
| `primitive/colors/slate-950` | #09090b | #fafafa | Dark background |

#### Colors - Brand
| Token | Value | Usage |
|-------|-------|-------|
| `primitive/colors/blue-500` | #4d7cff | Primary brand |
| `primitive/colors/blue-600` | #3b62fe | Hover state |
| `primitive/colors/blue-700` | #2d4de7 | Pressed state |

#### Spacing
| Token | Value |
|-------|-------|
| `primitive/spacing/0` | 0 |
| `primitive/spacing/1` | 4px |
| `primitive/spacing/2` | 8px |
| `primitive/spacing/3` | 12px |
| `primitive/spacing/4` | 16px |
| `primitive/spacing/6` | 24px |
| `primitive/spacing/8` | 32px |

#### Radius
| Token | Value |
|-------|-------|
| `primitive/radius/sm` | 4px |
| `primitive/radius/md` | 8px |
| `primitive/radius/lg` | 12px |

#### Font Size
| Token | Value |
|-------|-------|
| `primitive/fontSize/sm` | 14px |
| `primitive/fontSize/base` | 16px |
| `primitive/fontSize/lg` | 18px |
| `primitive/fontSize/2xl` | 24px |

### Semantic Variables

#### Colors
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `semantic/colors/background` | #ffffff | #171717 | Page bg |
| `semantic/colors/foreground` | #18181b | #fafafa | Main text |
| `semantic/colors/foreground-secondary` | #52525b | #a1a1aa | Secondary |
| `semantic/colors/foreground-muted` | #71717a | #71717a | Muted |
| `semantic/colors/primary` | #4d7cff | #4d7cff | Actions |
| `semantic/colors/primary-hover` | #3b62fe | #3b62fe | Hover |
| `semantic/colors/primary-foreground` | #ffffff | #ffffff | On primary |
| `semantic/colors/border` | #e4e4e7 | #3f3f46 | Borders |
| `semantic/colors/input-background` | #ffffff | #171717 | Inputs |
| `semantic/colors/input-placeholder` | #71717a | #71717a | Placeholder |

#### Spacing
| Token | Value |
|-------|-------|
| `semantic/padding/xs` | 4px |
| `semantic/padding/sm` | 8px |
| `semantic/padding/md` | 12px |
| `semantic/padding/lg` | 16px |
| `semantic/padding/xl` | 24px |

#### Gap
| Token | Value |
|-------|-------|
| `semantic/gap/xs` | 4px |
| `semantic/gap/sm` | 8px |
| `semantic/gap/md` | 12px |

#### Font Weight
| Token | Value |
|-------|-------|
| `semantic/weight/regular` | 400 |
| `semantic/weight/medium` | 500 |
| `semantic/weight/semibold` | 600 |
| `semantic/weight/bold` | 700 |

## Page Structure

### Intro
Professional design system documentation with:
- Title and version badge
- Color palette showcase
- Typography scale
- Spacing & radius visualization

### Atoms (Coming Soon)
Basic building blocks

### Molecules (Coming Soon)
Component combinations

### Organisms (Coming Soon)
Full UI sections

## Notes

⚠️ **Variable Alias Limitation**: Semantic variables store hardcoded values matching primitives. For true references, create aliases manually in Figma:
1. Right-click semantic variable
2. Select "Create variable alias"
3. Choose corresponding primitive

⚠️ **MCP Cache**: The MCP may show stale collection data. Always verify in Figma directly.

## MCP Commands

```javascript
// Get all variables
figma_get_variables({ format: "full" })

// Get variables by name
figma_get_variables({ 
  format: "full",
  namePattern: "^semantic" 
})

// Create variables (batch)
figma_setup_design_tokens({
  collectionName: "Design System V1",
  modes: ["Light", "Dark"],
  tokens: [...]
})
```

---
*Last updated: 2026-02-16*
*Built with Figma Console MCP*
