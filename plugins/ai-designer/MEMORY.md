# Figma AI Design System - Complete Production Knowledge Base

> **Production-ready design system** following Tailwind v4, Radix, and Figma 2024 best practices

---

## File Organization (Professional Structure)

```
Plugin Test (KsHzgtwa7iQ3HXuVBGoLsL)
├── 00 – Cover & Docs       # Documentation, changelog, stats
├── 01 – Foundations        # Design tokens (in Variable Collections)
├── 02 – Components         # Atomic design organized
│   ├── Header              # Page title and description
│   ├── Atoms               # Button, Badge, Input, Avatar, Switch, Tooltip
│   ├── Molecules           # Form Field, Navigation Item
│   └── Organisms           # Card, Modal
├── 03 – Patterns           # Form, Card, Navigation patterns ✓
├── 04 – Templates          # Full page layouts (empty)
└── Archive                 # Demonstration content only
```

## Quick Reference

| Collection | ID | Modes |
|------------|-----|-------|
| **Primitive** | `VariableCollectionId:64:177` | Light=64:7, Dark=64:8 |
| **Semantics** | `VariableCollectionId:64:208` | Light=64:9, Dark=64:10 |

**Total Variables**: 203 (138 Primitives + 65 Semantics)
**Component Sets**: 3 (Button, Badge, Navigation Item)
**Standalone Components**: 8 documented
**Styles**: 51 (11 Text + 40 Color)

---

## Token Exports

```
tokens/
├── css/
│   └── design-tokens.css     # CSS custom properties
├── json/
│   └── design-tokens.json    # Structured JSON (Style Dictionary compatible)
└── tailwind/
    └── tailwind.config.js    # Tailwind CSS config extension
```

---

## Variable Summary

| Category | Primitives | Semantics |
|----------|------------|-----------|
| Colors | 54 | 40 |
| Spacing | 17 | 1 + 12 (padding) + 9 (gap) |
| Radius | 7 | 5 |
| Font Size | 6 | 5 |
| Font Weight | 9 | 4 |
| Line Height | 7 | 4 |
| Letter Spacing | 6 | 3 |
| Opacity | 12 | 5 |
| Blur | 8 | 5 |
| Shadow | 21 | 1 |
| Font Family | 3 | 3 |
| **TOTAL** | **150** | **97** |

---

## Primitive Tokens

### Colors (54)

**Scales:** slate (11), blue (12), red (10), green (10), amber (10), white, black, transparent

```
primitive/colors/slate-50 through slate-950
primitive/colors/blue-50 through blue-900
primitive/colors/red-50 through red-900
primitive/colors/green-50 through green-900
primitive/colors/amber-50 through amber-900
primitive/colors/white
primitive/colors/black
primitive/colors/transparent
```

### Spacing (17)

| Token | Value | Notes |
|-------|-------|-------|
| primitive/spacing/0 | 0 | None |
| primitive/spacing/px | 1 | 1 pixel |
| primitive/spacing/1 | 4 | xs |
| primitive/spacing/1h | 6 | Half-step (1.5) |
| primitive/spacing/2 | 8 | sm |
| primitive/spacing/2h | 10 | Half-step (2.5) |
| primitive/spacing/3 | 12 | md |
| primitive/spacing/4 | 16 | lg |
| primitive/spacing/5 | 20 | |
| primitive/spacing/6 | 24 | xl |
| primitive/spacing/7 | 28 | |
| primitive/spacing/8 | 32 | 2xl |
| primitive/spacing/9 | 36 | |
| primitive/spacing/10 | 40 | 3xl |
| primitive/spacing/11 | 44 | |
| primitive/spacing/12 | 48 | 4xl |
| primitive/spacing/16 | 64 | 5xl |

### Radius (7)

| Token | Value |
|-------|-------|
| primitive/radius/0 | 0 |
| primitive/radius/sm | 4 |
| primitive/radius/md | 8 |
| primitive/radius/lg | 12 |
| primitive/radius/xl | 16 |
| primitive/radius/2xl | 24 |
| primitive/radius/full | 9999 |

### Font Size (6)

| Token | Value |
|-------|-------|
| primitive/fontSize/0 | 0 |
| primitive/fontSize/xs | 12 |
| primitive/fontSize/sm | 14 |
| primitive/fontSize/base | 16 |
| primitive/fontSize/lg | 18 |
| primitive/fontSize/2xl | 24 |

### Font Weight (9)

| Token | Value |
|-------|-------|
| primitive/weight/thin | 100 |
| primitive/weight/extralight | 200 |
| primitive/weight/light | 300 |
| primitive/weight/regular | 400 |
| primitive/weight/medium | 500 |
| primitive/weight/semibold | 600 |
| primitive/weight/bold | 700 |
| primitive/weight/extrabold | 800 |
| primitive/weight/black | 900 |

### Line Height (7)

| Token | Value |
|-------|-------|
| primitive/lineHeight/0 | 0 |
| primitive/lineHeight/none | 1 |
| primitive/lineHeight/tight | 1.25 |
| primitive/lineHeight/snug | 1.375 |
| primitive/lineHeight/normal | 1.5 |
| primitive/lineHeight/relaxed | 1.625 |
| primitive/lineHeight/loose | 2 |

### Letter Spacing (6)

| Token | Value |
|-------|-------|
| primitive/letterSpacing/tighter | -0.05 |
| primitive/letterSpacing/tight | -0.025 |
| primitive/letterSpacing/normal | 0 |
| primitive/letterSpacing/wide | 0.025 |
| primitive/letterSpacing/wider | 0.05 |
| primitive/letterSpacing/widest | 0.1 |

### Opacity (12)

| Token | Value |
|-------|-------|
| primitive/opacity/0 | 0 |
| primitive/opacity/5 | 5 |
| primitive/opacity/10 | 10 |
| primitive/opacity/20 | 20 |
| primitive/opacity/30 | 30 |
| primitive/opacity/40 | 40 |
| primitive/opacity/50 | 50 |
| primitive/opacity/60 | 60 |
| primitive/opacity/70 | 70 |
| primitive/opacity/80 | 80 |
| primitive/opacity/90 | 90 |
| primitive/opacity/100 | 100 |

### Opacity (5) → opacity primitives

| Semantic | Primitive | Value |
|----------|-----------|-------|
| opacity/0 | primitive/opacity/0 | 0 |
| opacity/disabled | primitive/opacity/50 | 50 |
| opacity/muted | primitive/opacity/70 | 70 |
| opacity/hover | primitive/opacity/80 | 80 |
| opacity/full | primitive/opacity/100 | 100 |

### Blur (5) → blur primitives

| Semantic | Value |
|----------|-------|
| blur/0 | 0 |
| blur/none | 0 |
| blur/sm | 4 |
| blur/md | 8 |
| blur/lg | 12 |

### Font Family (3) → fontFamily primitives

| Semantic | Value |
|----------|-------|
| fontFamily/body | "Inter" |
| fontFamily/heading | "Inter" |
| fontFamily/code | "JetBrains Mono" |

### Alignment (6 primitives → 4 semantics)

**Primitives:**
| Token | Value |
|-------|-------|
| primitive/alignment/min | "MIN" |
| primitive/alignment/center | "CENTER" |
| primitive/alignment/max | "MAX" |
| primitive/alignment/space-between | "SPACE_BETWEEN" |
| primitive/alignment/baseline | "BASELINE" |
| primitive/alignment/stretch | "STRETCH" |

**Semantics:**
| Semantic | Primitive |
|----------|-----------|
| alignment/primary-axis | MIN |
| alignment/counter-axis | CENTER |
| alignment/stretch | STRETCH |
| alignment/space-between | SPACE_BETWEEN |

---

## Components

### Component Sets (3 total)

| Component Set | Variants | Node IDs |
|---------------|----------|----------|
| **Button** | 5 (Default/Primary, Default/Secondary, Hover/Primary, Disabled/Primary, Focus/Primary) | 77:246 |
| **Badge** | 3 (Default, Success, Warning) | 77:247 |
| **Navigation Item** | 2 (Default, Active) | 76:215 |

### Individual Components (8 total)

| Component | Description | Node ID |
|-----------|-------------|---------|
| Input | Text input with placeholder | 64:339 |
| Card | Content container with title and description | 64:349 |
| Form Field | Label + input + helper text | 64:376 |
| Avatar | User avatar placeholder | 72:195 |
| Switch | Toggle switch | 72:197 |
| Tooltip | Information tooltip | 72:199 |
| Modal | Dialog container | 76:12 |

All properties bound including 0 values and opacity=100. Typography fully bound.

### Component Alignment Rules

| Component | Primary Axis | Counter Axis | Text Align |
|-----------|--------------|--------------|------------|
| Button | CENTER | CENTER | CENTER |
| Input | MIN | CENTER | LEFT |
| Badge (all) | CENTER | CENTER | CENTER |
| Card | MIN | MIN | LEFT |
| Navigation Item | MIN | CENTER | LEFT |
| Form Field | MIN | MIN | LEFT |
| Avatar | CENTER | CENTER | CENTER |
| Switch | MIN | CENTER | - |
| Tooltip | MIN | CENTER | CENTER |

### Component Set Bindings

| Component Set | Common Bindings |
|---------------|-----------------|
| **Button** | radius=md, padding=button-x/button-y, gap=button, opacity (disabled=50) |
| **Badge** | radius=full, padding=badge-x/badge-y, gap=badge |
| **Navigation Item** | padding=md/sm, gap=sm |

---

## Patterns (03 – Patterns Page)

| Pattern | Description | Components Used |
|---------|-------------|-----------------|
| **Login Form** | Email + Password + Submit button | Input, Button |
| **Product Card** | Image + Title + Description + Price + Action | Card, Button, Badge |
| **Sidebar Navigation** | Logo + Nav Items with active state | Navigation Item, Avatar |

### Pattern Usage
- Use patterns as starting points for common UI sections
- Customize with component variants (State, Size, Type)
- Bind to semantic tokens for theming

---

## Text Styles (11 total)

| Style | Font Size | Weight | Line Height | Letter Spacing | Font Family |
|-------|-----------|--------|-------------|----------------|-------------|
| Heading/Display | 2xl | Bold | Tight | Tight | Heading |
| Heading/H1 | xl | Bold | Tight | Tight | Heading |
| Heading/H2 | lg | Semibold | Tight | Normal | Heading |
| Heading/H3 | base | Semibold | Normal | Normal | Heading |
| Body/Large | base | Regular | Normal | Normal | Body |
| Body/Default | sm | Regular | Normal | Normal | Body |
| Body/Small | xs | Regular | Normal | Normal | Body |
| Label/Default | sm | Medium | Normal | Normal | Body |
| Label/Small | xs | Medium | Normal | Normal | Body |
| Code/Default | sm | Regular | Normal | Wide | Code |
| Code/Small | xs | Regular | Normal | Wide | Code |

---

## Color Styles (40 total)

Semantic color styles created from resolved token values:
- background, foreground, foreground-secondary, foreground-muted
- primary, primary-hover, primary-foreground
- secondary, secondary-foreground, secondary-hover, secondary-active
- border, ring, muted, muted-foreground
- accent, accent-foreground
- card, card-foreground, card-image
- popover, popover-foreground
- destructive, destructive-foreground, destructive-hover, destructive-active
- success, success-foreground
- warning, warning-foreground
- input-background, input-placeholder, input-border, input-hover, input-focus, input-disabled
- button-hover, button-active, button-disabled
- focus-ring

---

## Binding Stats

| Property | Bound Count |
|----------|-------------|
| cornerRadius | 17 |
| padding | 17 |
| gap | 17 |
| fontWeight | 14 |
| fontSize | 14 |
| opacity | 31 |
| fills | 29 |
| strokes | 5 |

---

## Code Patterns

### Create Primitive
```javascript
const v = figma.variables.createVariable('primitive/spacing/2h', primCollection, 'FLOAT');
v.setValueForMode('64:7', 10);
v.setValueForMode('64:8', 10);
```

### Create Semantic with Alias
```javascript
const primVar = allVars.find(v => v.name === 'primitive/spacing/4');
const semVar = figma.variables.createVariable('semantic/padding/button-x', semCollection, 'FLOAT');
const alias = figma.variables.createVariableAlias(primVar);
semVar.setValueForMode('64:9', alias);
semVar.setValueForMode('64:10', alias);
```

### Bind All Properties (including 0)
```javascript
// Corner radius (including 0)
node.setBoundVariable('topLeftRadius', semVars['semantic/radius/md']);
node.setBoundVariable('topRightRadius', semVars['semantic/radius/md']);
node.setBoundVariable('bottomRightRadius', semVars['semantic/radius/md']);
node.setBoundVariable('bottomLeftRadius', semVars['semantic/radius/md']);

// Padding (including 0)
node.setBoundVariable('paddingLeft', semVars['semantic/padding/xl']);
node.setBoundVariable('paddingRight', semVars['semantic/padding/xl']);
node.setBoundVariable('paddingTop', semVars['semantic/padding/md']);
node.setBoundVariable('paddingBottom', semVars['semantic/padding/md']);

// Gap (including 0)
node.setBoundVariable('itemSpacing', semVars['semantic/gap/sm']);

// Opacity (including 1 = full)
node.setBoundVariable('opacity', semVars['semantic/opacity/full']);

// Typography
node.setBoundVariable('fontSize', semVars['semantic/fontSize/base']);
node.setBoundVariable('fontWeight', semVars['semantic/weight/medium']);
node.setBoundVariable('lineHeight', semVars['semantic/lineHeight/normal']);
node.setBoundVariable('letterSpacing', semVars['semantic/letterSpacing/normal']);
node.setBoundVariable('fontFamily', semVars['semantic/fontFamily/body']);

// Colors
node.fills = [{
  type: 'SOLID',
  color: { r: 0.2, g: 0.5, b: 0.95 },
  boundVariables: { color: figma.variables.createVariableAlias(semVars['semantic/colors/primary']) }
}];
```

### Set Auto-Layout Alignment
```javascript
// Button/Badge: Center content
comp.primaryAxisAlignItems = 'MIN';      // Left-to-right start
comp.counterAxisAlignItems = 'CENTER';   // Vertically centered
text.textAlignHorizontal = 'CENTER';

// Input: Left-aligned text
comp.primaryAxisAlignItems = 'MIN';
comp.counterAxisAlignItems = 'CENTER';
text.textAlignHorizontal = 'LEFT';

// Card: Top-left content
comp.primaryAxisAlignItems = 'MIN';
comp.counterAxisAlignItems = 'MIN';
text.textAlignHorizontal = 'LEFT';

// Navigation: Left-aligned
comp.primaryAxisAlignItems = 'MIN';
comp.counterAxisAlignItems = 'CENTER';
text.textAlignHorizontal = 'LEFT';
```

---

## Value Mappings for Fixes

### Corner Radius
```javascript
{ 0: 'semantic/radius/0', 8: 'semantic/radius/md', 12: 'semantic/radius/lg', 9999: 'semantic/radius/full' }
```

### Padding
```javascript
{ 0: 'semantic/padding/0', 4: 'semantic/padding/badge-y', 8: 'semantic/padding/badge-x', 
  10: 'semantic/padding/button-y', 12: 'semantic/padding/input-x', 16: 'semantic/padding/button-x', 
  24: 'semantic/padding/xl' }
```

### Gap
```javascript
{ 0: 'semantic/gap/0', 6: 'semantic/gap/badge', 8: 'semantic/gap/button', 
  12: 'semantic/gap/card', 16: 'semantic/gap/form' }
```

### Font Weight
```javascript
{ 400: 'semantic/weight/regular', 500: 'semantic/weight/medium', 
  600: 'semantic/weight/semibold', 700: 'semantic/weight/bold' }
```

### Opacity
```javascript
{ 0: 'semantic/opacity/0', 1: 'semantic/opacity/full' }
// Note: Primitive values are 0-100 scale, not 0-1
```

### Color Hex
```javascript
{ '#ffffff': 'semantic/colors/background', '#f0f5fa': 'semantic/colors/secondary',
  '#e0e3e8': 'semantic/colors/border', '#171c26': 'semantic/colors/foreground',
  '#737a87': 'semantic/colors/foreground-muted', '#99a1ab': 'semantic/colors/input-placeholder',
  '#2e66d1': 'semantic/colors/primary-hover', '#387df2': 'semantic/colors/primary',
  '#0ab87d': 'semantic/colors/success', '#f2ab12': 'semantic/colors/warning' }
```

---

## Rules

1. **ALL semantics must alias to primitives** - No hardcoded values in semantics
2. **ALL component properties must be bound** - Including 0 values and opacity=1
3. **NEVER bind directly to primitives** - Always use semantic tokens
4. **Half-step values use 'h' suffix** - 1h=6, 2h=10 (can't use dots in names)

---

## File Info

- **File**: "Plugin Test" (KsHzgtwa7iQ3HXuVBGoLsL)
- **MCP**: figma-console via Desktop Bridge (port 9226)
- **Total Variables**: 203 (138 primitives + 65 semantics)
- **Component Sets**: 3 (Button=5, Badge=3, Navigation Item=2)
- **Individual Components**: 8
- **Styles**: 51 (11 text + 40 color)

---

## Professional Design System Organization (2024-2026 Best Practices)

### Page Structure Standard
```
00 – Cover & Docs          # Changelog, team credits, links
01 – Foundations / Tokens  # Variables, colors, typography, spacing
02 – Components            # Component sets organized by atomic category
03 – Patterns              # Combined components (forms, cards, etc)
04 – Templates             # Full page layouts
05 – Brand Themes          # Multi-brand variations (optional)
06 – Dev Handoff           # Specs, annotations (optional)
Archive                    # Deprecated items
```

### Atomic Design Categories
| Category | Description | Examples |
|----------|-------------|----------|
| **Atoms** | Smallest UI elements | Button, Input, Badge, Icon |
| **Molecules** | Simple combinations | Form Field, Navigation Item |
| **Organisms** | Complex components | Card, Modal, DataTable |
| **Templates** | Page compositions | Dashboard, Settings |
| **Pages** | Final implementations | Specific screens |

### Component Set Naming
- Use `Property=Value` format: `State=Default, Variant=Primary`
- Group by primary variant first: State, Size, then Variant
- Max 10 variants per set for maintainability

### Dev Mode Documentation Template
```markdown
## Description
Brief component purpose

## Variants
- **Variant A**: Description
- **Variant B**: Description

## Properties
- **propName**: Values

## States
- Default, Hover, Focus, Disabled, Error

## Accessibility
- ARIA attributes
- Keyboard interactions

## Code
```tsx
<Component prop="value">Content</Component>
```
```

---

*Last updated: 2026-02-18*
*File reorganized with professional page structure ✓*
*Atomic design categorization implemented ✓*
*All components documented with Dev Mode descriptions ✓*
*Accessibility annotations added ✓*
