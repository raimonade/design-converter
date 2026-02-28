# Component Architecture - Professional Design System

> Complete guide for building professional Figma components - 2026-02-12

---

## 1. Component Resizing Patterns

### Width/Height Behaviors

| Pattern | When to Use | Code |
|---------|-------------|------|
| **Fixed Size** | Buttons, inputs, icons | `width: 120, height: 40` |
| **Hug Contents** | Labels, badges, buttons | `width: "fit_content", height: "fit_content"` |
| **Fill Container** | Cards in grids, content areas | `width: "fill_container", height: "fill_container"` |
| **Fill Width Only** | Headers, full-width elements | `width: "fill_container", height: 60` |
| **Fill Height Only** | Sidebars, vertical nav | `width: 240, height: "fill_container"` |

### Internal Element Scaling

```javascript
// Element that scales LEFT + RIGHT (horizontal stretch)
{
  "width": "fill_container",
  "layoutAlign": "STRETCH",
  "constraints": { "horizontal": "SCALE", "vertical": "TOP" }
}

// Element that scales TOP + BOTTOM (vertical stretch)
{
  "height": "fill_container",
  "layoutAlign": "STRETCH",
  "constraints": { "horizontal": "LEFT", "vertical": "STRETCH" }
}

// Element that scales BOTH directions
{
  "width": "fill_container",
  "height": "fill_container",
  "layoutAlign": "STRETCH",
  "constraints": { "horizontal": "SCALE", "vertical": "STRETCH" }
}
```

### Auto-Layout Resizing

```javascript
// Container that hugs content (buttons, labels)
frame.primaryAxisSizingMode = 'HUG';
frame.counterAxisSizingMode = 'HUG';

// Container that fills parent (cards, sections)
frame.primaryAxisSizingMode = 'FIXED';
frame.counterAxisSizingMode = 'FILL';

// Mixed: fixed width, hug height
frame.primaryAxisSizingMode = 'HUG';
frame.counterAxisSizingMode = 'FIXED';
frame.resize(300, 0);  // Width fixed, height auto
```

---

## 2. Complete Token Taxonomy

### Token Hierarchy
```
PRIMITIVE → SEMANTIC → COMPONENT
   ↓            ↓           ↓
Raw values   Purpose    Specific use
```

### Color Tokens

```javascript
// PRIMITIVE COLORS (raw palette)
{
  "--blue-50": { "type": "color", "value": "#eff6ff" },
  "--blue-500": { "type": "color", "value": "#3b82f6" },
  "--blue-900": { "type": "color", "value": "#1e3a8a" },
  "--gray-50": { "type": "color", "value": "#f9fafb" },
  "--gray-500": { "type": "color", "value": "#6b7280" },
  "--gray-900": { "type": "color", "value": "#111827" }
}

// SEMANTIC COLORS (purpose)
{
  "--primary": { "type": "color", "value": "$--blue-500" },
  "--primary-foreground": { "type": "color", "value": "#ffffff" },
  "--background": { "type": "color", "value": "$--gray-50" },
  "--foreground": { "type": "color", "value": "$--gray-900" },
  "--muted": { "type": "color", "value": "$--gray-100" },
  "--border": { "type": "color", "value": "$--gray-200" }
}

// COMPONENT COLORS (specific use)
{
  "--button-bg": { "type": "color", "value": "$--primary" },
  "--button-text": { "type": "color", "value": "$--primary-foreground" },
  "--input-bg": { "type": "color", "value": "$--background" },
  "--input-border": { "type": "color", "value": "$--border" }
}
```

### Spacing Tokens

```javascript
// 4px base scale
{
  "--spacing-0": { "type": "number", "value": 0 },
  "--spacing-1": { "type": "number", "value": 4 },
  "--spacing-2": { "type": "number", "value": 8 },
  "--spacing-3": { "type": "number", "value": 12 },
  "--spacing-4": { "type": "number", "value": 16 },
  "--spacing-5": { "type": "number", "value": 20 },
  "--spacing-6": { "type": "number", "value": 24 },
  "--spacing-8": { "type": "number", "value": 32 },
  "--spacing-10": { "type": "number", "value": 40 },
  "--spacing-12": { "type": "number", "value": 48 },
  "--spacing-16": { "type": "number", "value": 64 },
  "--spacing-20": { "type": "number", "value": 80 }
}

// Semantic spacing
{
  "--padding-sm": { "type": "number", "value": "$--spacing-2" },
  "--padding-md": { "type": "number", "value": "$--spacing-4" },
  "--padding-lg": { "type": "number", "value": "$--spacing-6" },
  "--gap-sm": { "type": "number", "value": "$--spacing-2" },
  "--gap-md": { "type": "number", "value": "$--spacing-4" }
}
```

### Border/Radius Tokens

```javascript
// Border width
{
  "--border-0": { "type": "number", "value": 0 },
  "--border-1": { "type": "number", "value": 1 },
  "--border-2": { "type": "number", "value": 2 },
  "--border-4": { "type": "number", "value": 4 }
}

// Border radius
{
  "--radius-none": { "type": "number", "value": 0 },
  "--radius-sm": { "type": "number", "value": 4 },
  "--radius-md": { "type": "number", "value": 8 },
  "--radius-lg": { "type": "number", "value": 12 },
  "--radius-xl": { "type": "number", "value": 16 },
  "--radius-2xl": { "type": "number", "value": 24 },
  "--radius-full": { "type": "number", "value": 9999 }
}
```

### Shadow/Effect Tokens

```javascript
// Box shadows
{
  "--shadow-sm": { "type": "string", "value": "0 1px 2px 0 rgba(0,0,0,0.05)" },
  "--shadow-md": { "type": "string", "value": "0 4px 6px -1px rgba(0,0,0,0.1)" },
  "--shadow-lg": { "type": "string", "value": "0 10px 15px -3px rgba(0,0,0,0.1)" },
  "--shadow-xl": { "type": "string", "value": "0 20px 25px -5px rgba(0,0,0,0.1)" }
}

// Blur
{
  "--blur-none": { "type": "number", "value": 0 },
  "--blur-sm": { "type": "number", "value": 4 },
  "--blur-md": { "type": "number", "value": 8 },
  "--blur-lg": { "type": "number", "value": 16 }
}

// Opacity
{
  "--opacity-0": { "type": "number", "value": 0 },
  "--opacity-5": { "type": "number", "value": 0.05 },
  "--opacity-10": { "type": "number", "value": 0.1 },
  "--opacity-20": { "type": "number", "value": 0.2 },
  "--opacity-50": { "type": "number", "value": 0.5 },
  "--opacity-75": { "type": "number", "value": 0.75 },
  "--opacity-100": { "type": "number", "value": 1 }
}
```

### Typography Tokens

```javascript
// Font family
{
  "--font-sans": { "type": "string", "value": "Inter, system-ui, sans-serif" },
  "--font-mono": { "type": "string", "value": "SF Mono, monospace" }
}

// Font size
{
  "--text-xs": { "type": "number", "value": 12 },
  "--text-sm": { "type": "number", "value": 14 },
  "--text-base": { "type": "number", "value": 16 },
  "--text-lg": { "type": "number", "value": 18 },
  "--text-xl": { "type": "number", "value": 20 },
  "--text-2xl": { "type": "number", "value": 24 },
  "--text-3xl": { "type": "number", "value": 30 },
  "--text-4xl": { "type": "number", "value": 36 },
  "--text-5xl": { "type": "number", "value": 48 }
}

// Font weight
{
  "--font-normal": { "type": "number", "value": 400 },
  "--font-medium": { "type": "number", "value": 500 },
  "--font-semibold": { "type": "number", "value": 600 },
  "--font-bold": { "type": "number", "value": 700 }
}

// Line height
{
  "--leading-none": { "type": "number", "value": 1 },
  "--leading-tight": { "type": "number", "value": 1.25 },
  "--leading-snug": { "type": "number", "value": 1.375 },
  "--leading-normal": { "type": "number", "value": 1.5 },
  "--leading-relaxed": { "type": "number", "value": 1.625 },
  "--leading-loose": { "type": "number", "value": 2 }
}
```

---

## 3. Component Naming Convention

### Pattern
```
[Category]/[Variant]/[Size]/[State]

Examples:
- Button/Primary/Large
- Button/Outline/Small
- Input/Default/Error
- Badge/Success
- Avatar/Large
- Card/Highlight
```

### Category Prefixes
| Category | Examples |
|----------|----------|
| **Button** | Button/Primary, Button/Secondary, Button/Outline |
| **Input** | Input/Default, Input/Focus, Input/Error |
| **Badge** | Badge/Default, Badge/Success, Badge/Error |
| **Avatar** | Avatar/Small, Avatar/Default, Avatar/Large |
| **Text** | Text/Heading/1, Text/Body/Default, Text/Label |
| **Card** | Card/Default, Card/Highlight, Card/Action |
| **Alert** | Alert/Success, Alert/Warning, Alert/Error |

---

## 4. Component Internal Structure

### Button Example

```javascript
// Button with all internal elements properly structured
async function createButton() {
  const button = figma.createFrame();
  button.name = 'Button/Primary';
  button.layoutMode = 'HORIZONTAL';
  button.primaryAxisSizingMode = 'HUG';
  button.counterAxisSizingMode = 'HUG';
  button.itemSpacing = 8;
  button.paddingLeft = 16;
  button.paddingRight = 16;
  button.paddingTop = 10;
  button.paddingBottom = 10;
  button.primaryAxisAlignItems = 'CENTER';
  button.counterAxisAlignItems = 'CENTER';
  button.cornerRadius = 6;
  
  // Bind fill to variable
  const primaryBg = await getVariable('--button-bg');
  button.fills = [{
    type: 'SOLID',
    color: { type: 'VARIABLE_ALIAS', id: primaryBg.id }
  }];
  
  // Icon slot (optional)
  const iconSlot = figma.createFrame();
  iconSlot.name = 'iconSlot';
  iconSlot.layoutMode = 'NONE';
  iconSlot.width = 16;
  iconSlot.height = 16;
  button.appendChild(iconSlot);
  
  // Text (using Text component ref)
  const textRef = textLabelComponent.createInstance();
  textRef.setProperties({ "Content": "Button" });
  button.appendChild(textRef);
  
  return figma.createComponentFromNode(button);
}
```

### Card Example (with slots)

```javascript
async function createCard() {
  const card = figma.createFrame();
  card.name = 'Card';
  card.layoutMode = 'VERTICAL';
  card.primaryAxisSizingMode = 'HUG';
  card.counterAxisSizingMode = 'FIXED';  // Fixed height or fill
  card.itemSpacing = 16;
  card.paddingLeft = 24;
  card.paddingRight = 24;
  card.paddingTop = 24;
  card.paddingBottom = 24;
  card.cornerRadius = 12;
  
  // Bind variables
  const cardBg = await getVariable('--card');
  card.fills = [{
    type: 'SOLID',
    color: { type: 'VARIABLE_ALIAS', id: cardBg.id }
  }];
  
  // Header slot (fills width)
  const headerSlot = figma.createFrame();
  headerSlot.name = 'headerSlot';
  headerSlot.layoutMode = 'HORIZONTAL';
  headerSlot.primaryAxisSizingMode = 'FILL';
  headerSlot.counterAxisSizingMode = 'HUG';
  headerSlot.layoutAlign = 'STRETCH';  // Fills container width
  card.appendChild(headerSlot);
  
  // Content slot (fills both directions)
  const contentSlot = figma.createFrame();
  contentSlot.name = 'contentSlot';
  contentSlot.layoutMode = 'VERTICAL';
  contentSlot.primaryAxisSizingMode = 'HUG';
  contentSlot.counterAxisSizingMode = 'FILL';
  contentSlot.layoutAlign = 'STRETCH';
  contentSlot.layoutGrow = 1;  // Takes remaining space
  card.appendChild(contentSlot);
  
  // Actions slot (fills width, right-aligned)
  const actionsSlot = figma.createFrame();
  actionsSlot.name = 'actionsSlot';
  actionsSlot.layoutMode = 'HORIZONTAL';
  actionsSlot.primaryAxisSizingMode = 'FILL';
  actionsSlot.counterAxisSizingMode = 'HUG';
  actionsSlot.layoutAlign = 'STRETCH';
  actionsSlot.primaryAxisAlignItems = 'MAX';  // Right align
  actionsSlot.itemSpacing = 8;
  card.appendChild(actionsSlot);
  
  return figma.createComponentFromNode(card);
}
```

---

## 5. Variant Patterns

### Size Variants (Separate Components)

```javascript
// Size variants have different dimensions/padding - create separate components
const sizes = {
  sm: { height: 32, padding: [6, 12], fontSize: 14 },
  md: { height: 40, padding: [10, 16], fontSize: 14 },
  lg: { height: 48, padding: [12, 24], fontSize: 16 }
};

for (const [size, config] of Object.entries(sizes)) {
  const button = createButtonFrame(config);
  const component = figma.createComponentFromNode(button);
  component.name = `Button/${size.charAt(0).toUpperCase() + size.slice(1)}`;
}
```

### State Variants (Refs with Overrides)

```javascript
// Base: Input/Default
const inputDefault = figma.createComponentFromNode(inputFrame);
inputDefault.name = 'Input/Default';

// Variant: Input/Focus (ref with different stroke)
const inputFocus = inputDefault.createInstance();
inputFocus.name = 'Input/Focus';
inputFocus.strokes = [{
  type: 'SOLID',
  color: { type: 'VARIABLE_ALIAS', id: focusBorderVar.id }
}];
inputFocus.strokeWeight = 2;

// Variant: Input/Error (ref with different stroke)
const inputError = inputDefault.createInstance();
inputError.name = 'Input/Error';
inputError.strokes = [{
  type: 'SOLID',
  color: { type: 'VARIABLE_ALIAS', id: errorBorderVar.id }
}];
```

### Style Variants (Fill/Border Combinations)

```javascript
// Button styles defined by fill + stroke + text color combinations
const styles = {
  primary: {
    fill: '$--primary',
    stroke: null,
    textColor: '$--primary-foreground'
  },
  secondary: {
    fill: '$--secondary',
    stroke: null,
    textColor: '$--secondary-foreground'
  },
  outline: {
    fill: 'transparent',
    stroke: '$--border',
    textColor: '$--foreground'
  },
  ghost: {
    fill: 'transparent',
    stroke: null,
    textColor: '$--foreground'
  }
};
```

---

## 6. Component Properties

### Property Types

```javascript
// Text property (for content)
component.addComponentProperty("Label", 'TEXT', "Button");

// Boolean property (for visibility)
component.addComponentProperty("Show Icon", 'BOOLEAN', true);

// Variant property (for dropdown)
component.addComponentProperty("Size", 'VARIANT', "Medium", {
  variantOptions: ['Small', 'Medium', 'Large']
});

// Instance swap property (for icons)
component.addComponentProperty("Icon", 'INSTANCE_SWAP', 'defaultIconId');
```

---

## 7. Anti-Patterns to Avoid

| Pattern | Problem | Solution |
|---------|---------|----------|
| Hardcoded spacing | Can't scale | Use `$--spacing-X` |
| Hardcoded colors | Can't theme | Use semantic tokens |
| Fixed main frame | Clips content | Use `fit_content` |
| Inline in molecules | Inconsistent | Use refs to atoms |
| No auto-layout | Rigid | Add layout properties |
| Missing line-height | Poor readability | Set appropriate value |
| Same color bg/text | Invisible | Ensure contrast |

---

## 8. Quality Checklist

Before finalizing a component:

- [ ] Uses semantic tokens (not primitives directly)
- [ ] Proper auto-layout (gap, padding, alignment)
- [ ] Resizing behavior correct (hug/fill/fixed)
- [ ] All spacing uses variables
- [ ] All colors bound to variables
- [ ] Component properties defined
- [ ] Variants created (size, state, style)
- [ ] Slots defined (for organisms)
- [ ] WCAG contrast verified
- [ ] Font is literal string (not variable)
