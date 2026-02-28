# Design System Patterns - Quick Reference

> Essential patterns for LLM-generated design systems - 2026-02-12

---

## 1. Token Architecture

### Three-Layer Pattern
```
Primitive → Semantic → Component
```

**Primitives** (raw values):
```json
{ "color-blue-500": "#3B82F6" }
{ "spacing-16": "16px" }
{ "font-size-xl": "20px" }
```

**Semantics** (purpose):
```json
{ "color-primary": "$color-blue-500" }
{ "spacing-md": "$spacing-16" }
{ "text-heading": "$font-size-xl" }
```

---

## 2. Atomic Design Hierarchy

```
Atoms → Molecules → Organisms → Templates → Pages
```

| Level | Definition | Examples |
|-------|------------|----------|
| **Atoms** | Cannot decompose | Button, Input, Badge, Text |
| **Molecules** | 2-4 atoms combined | InputGroup, SearchBox, ListItem |
| **Organisms** | Complex sections | Card, Sidebar, Header |

---

## 3. Text Components (Typography)

### Text Hierarchy
```
Text/
├── Heading/1 (48px Bold)
├── Heading/2 (36px Bold)
├── Heading/3 (24px SemiBold)
├── Body/Default (16px Regular)
├── Body/Small (14px Regular)
├── Label/Default (14px Medium)
└── Caption (12px Regular Muted)
```

### Text with Variable Binding
```javascript
// Create text component with token binding
const text = figma.createText();
text.fontSize = 24;  // Maps to --font-size-2xl
text.fontName = { family: 'Inter', style: 'SemiBold' };
text.textAutoResize = 'WIDTH_AND_HEIGHT';  // Hug content

// Bind color to variable
text.fills = [{
  type: 'SOLID',
  color: { type: 'VARIABLE_ALIAS', id: textPrimaryVar.id }
}];

// Add content property
component.addComponentProperty("Content", 'TEXT', "Default Text");
```

### Autolayout Options
```javascript
// Hug content (default for text)
text.textAutoResize = 'WIDTH_AND_HEIGHT';

// Fill width, grow height
text.textAutoResize = 'HEIGHT';
text.layoutAlign = 'STRETCH';
```

---

## 4. Component Variants

### Size Variants (separate components)
```
Button/Default (40px)
Button/Large (48px)
Button/Small (32px)
```

### State Variants (refs with overrides)
```
TabItem/Active (base)
TabItem/Inactive (ref with different fill)
```

### Style Variants (fill/border combinations)
```
Button/Primary (bg: primary, text: white)
Button/Outline (bg: transparent, border: primary)
```

---

## 5. Slot Pattern

**Purpose**: Flexible content injection without prop bloat

```javascript
// Component with slots
Card = {
  header: { slot: [] },
  content: { slot: [] },
  actions: { slot: [] }
}

// Usage with Text refs
MyCard = createInstance(Card)
insert(MyCard.header, { type: "ref", "ref": "Text/Heading/3" })
insert(MyCard.content, { type: "ref", "ref": "Text/Body/Default" })
```

---

## 6. Essential Token Set

### Colors
```css
--primary, --primary-foreground
--secondary, --secondary-foreground
--background, --foreground
--muted, --muted-foreground
--border, --success, --warning, --error
--text-primary, --text-secondary, --text-muted
```

### Spacing (4px base)
```css
--spacing-1: 4px
--spacing-2: 8px
--spacing-3: 12px
--spacing-4: 16px
--spacing-6: 24px
--spacing-8: 32px
```

### Typography
```css
--font-size-xs: 12px
--font-size-sm: 14px
--font-size-base: 16px
--font-size-lg: 18px
--font-size-xl: 20px
--font-size-2xl: 24px
--font-size-3xl: 36px
--font-size-4xl: 48px

--font-weight-normal: 400
--font-weight-medium: 500
--font-weight-semibold: 600
--font-weight-bold: 700

--line-height-tight: 1.25
--line-height-normal: 1.5
```

---

## 7. Layout Rules

### Main Frame
```javascript
{
  width: "fit_content",
  height: "fit_content",
  clip: false,  // NEVER clip!
  layout: "vertical"
}
```

### Atoms (Buttons, Badges, Text)
```javascript
{
  layout: "horizontal",
  justifyContent: "center",
  alignItems: "center",
  gap: 8,
  padding: [12, 24]
}
```

### Text Components
```javascript
{
  textAutoResize: "WIDTH_AND_HEIGHT",  // Hug content
  lineHeight: { value: 150, unit: "PERCENT" }
}
```

---

## 8. Anti-Patterns (AVOID)

| Pattern | Why Bad | Correct Approach |
|---------|---------|------------------|
| Raw hex values | Can't theme | Use semantic tokens |
| Fixed main frame | Clips content | Use fit_content |
| Inline duplicates | Maintenance hell | Use refs |
| No text components | Inconsistent typography | Create Text/* components |
| Missing line height | Poor readability | Set appropriate line height |

---

Sources: PencilDev AGENTS.md, EMBER Design System, shadcn/ui patterns
