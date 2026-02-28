# Text Components System

> Typography as reusable components with variable binding - 2026-02-12

---

## Why Text Components?

**Benefits:**
1. **Size control** - Consistent typography across the system
2. **Content control** - Centralized text styling
3. **Autolayout control** - Define if text hugs content or fills container
4. **Variable binding** - Map typeface tokens to components

---

## Text Component Structure

### Hierarchy
```
Text/
├── Heading/1 (H1 - 48px, Bold)
├── Heading/2 (H2 - 36px, Bold)
├── Heading/3 (H3 - 24px, SemiBold)
├── Body/Large (18px, Regular)
├── Body/Default (16px, Regular)
├── Body/Small (14px, Regular)
├── Label/Default (14px, Medium)
├── Label/Small (12px, Medium)
└── Caption (12px, Regular, Muted)
```

---

## Variable Binding Pattern

### Typography Tokens
```javascript
// Create typography variables
const typographyTokens = {
  "--font-size-xs": 12,
  "--font-size-sm": 14,
  "--font-size-base": 16,
  "--font-size-lg": 18,
  "--font-size-xl": 20,
  "--font-size-2xl": 24,
  "--font-size-3xl": 30,
  "--font-size-4xl": 48,
  "--font-weight-normal": "400",
  "--font-weight-medium": "500",
  "--font-weight-semibold": "600",
  "--font-weight-bold": "700",
  "--font-family-sans": "Inter",
  "--line-height-tight": 1.25,
  "--line-height-normal": 1.5,
  "--line-height-relaxed": 1.75
};
```

### Text Component with Variables
```javascript
async function createHeading1() {
  // Create text node
  await figma.loadFontAsync({ family: 'Inter', style: 'Bold' });
  const text = figma.createText();
  text.characters = "Heading 1";
  
  // Bind to variables
  const fontSizeVar = await getVariable("--font-size-4xl");
  const fontWeightVar = await getVariable("--font-weight-bold");
  const fontFamilyVar = await getVariable("--font-family-sans");
  const lineHeightVar = await getVariable("--line-height-tight");
  
  text.setBoundVariable('fontSize', fontSizeVar);
  text.setBoundVariable('fontName', fontFamilyVar);
  
  // Manual values (Figma API limitation)
  text.fontSize = 48;
  text.fontName = { family: 'Inter', style: 'Bold' };
  text.lineHeight = { value: 1.25, unit: 'PERCENT' };
  
  // Convert to component
  const component = figma.createComponentFromNode(text);
  component.name = 'Text/Heading/1';
  component.description = 'H1 - 48px Bold';
  
  // Add text property for content
  component.addComponentProperty("Content", 'TEXT', "Heading 1");
  
  return component;
}
```

---

## Autolayout Control

### Text That Hugs Content (Default)
```javascript
// Most text components hug their content
text.textAutoResize = 'WIDTH_AND_HEIGHT';
// Result: Text frame shrinks to fit content
```

### Text That Fills Container
```javascript
// For text inside fixed-width containers
text.textAutoResize = 'HEIGHT';  // Width fixed, height grows
text.layoutAlign = 'STRETCH';     // Fill horizontal space
```

### Text with Max Width
```javascript
// Constrained text (like in cards)
const container = figma.createFrame();
container.resize(300, 200);
container.layoutMode = 'VERTICAL';

const text = figma.createText();
text.characters = "Long description text...";
text.textAutoResize = 'HEIGHT';
text.layoutAlign = 'STRETCH';
// Text will wrap at 300px width
```

---

## Complete Text Component Set

```javascript
async function createTextComponents() {
  const components = [];
  
  // Define text styles
  const textStyles = [
    { name: 'Heading/1', size: 48, weight: 'Bold', lineHeight: 1.25 },
    { name: 'Heading/2', size: 36, weight: 'Bold', lineHeight: 1.25 },
    { name: 'Heading/3', size: 24, weight: 'SemiBold', lineHeight: 1.3 },
    { name: 'Heading/4', size: 20, weight: 'SemiBold', lineHeight: 1.3 },
    { name: 'Body/Large', size: 18, weight: 'Regular', lineHeight: 1.5 },
    { name: 'Body/Default', size: 16, weight: 'Regular', lineHeight: 1.5 },
    { name: 'Body/Small', size: 14, weight: 'Regular', lineHeight: 1.5 },
    { name: 'Label/Default', size: 14, weight: 'Medium', lineHeight: 1.4 },
    { name: 'Label/Small', size: 12, weight: 'Medium', lineHeight: 1.4 },
    { name: 'Caption', size: 12, weight: 'Regular', lineHeight: 1.4 }
  ];
  
  for (const style of textStyles) {
    await figma.loadFontAsync({ family: 'Inter', style: style.weight });
    
    const text = figma.createText();
    text.characters = style.name;
    text.fontSize = style.size;
    text.fontName = { family: 'Inter', style: style.weight };
    text.lineHeight = { value: style.lineHeight * 100, unit: 'PERCENT' };
    text.textAutoResize = 'WIDTH_AND_HEIGHT';
    
    const component = figma.createComponentFromNode(text);
    component.name = `Text/${style.name}`;
    component.addComponentProperty("Content", 'TEXT', style.name);
    
    components.push(component);
  }
  
  return components;
}
```

---

## Using Text Components

### In Molecules
```javascript
// Card using Text refs
async function createCard() {
  const card = figma.createFrame();
  card.layoutMode = 'VERTICAL';
  card.itemSpacing = 12;
  
  // Heading ref
  const title = await createTextRef('Text/Heading/3', "Card Title");
  card.appendChild(title);
  
  // Body ref
  const body = await createTextRef('Text/Body/Default', "Description text here...");
  card.appendChild(body);
  
  // Label ref
  const label = await createTextRef('Text/Label/Small', "Category");
  card.appendChild(label);
  
  return card;
}
```

### With Content Override
```javascript
// Create instance and override content
const heading = heading1Component.createInstance();
heading.setProperties({
  "Content": "Custom Heading Text"
});
```

---

## Mapping Variables to Text Properties

### Token → Component Mapping
```javascript
const tokenMapping = {
  // Token → Text Property
  "--font-size-4xl": "fontSize → Text/Heading/1",
  "--font-size-3xl": "fontSize → Text/Heading/2",
  "--font-size-2xl": "fontSize → Text/Heading/3",
  "--font-weight-bold": "fontWeight → Text/Heading/*",
  "--font-weight-medium": "fontWeight → Text/Label/*",
  "--line-height-tight": "lineHeight → Text/Heading/*",
  "--line-height-normal": "lineHeight → Text/Body/*"
};
```

### Theme-Aware Text Colors
```javascript
// Create color tokens for text
const textColorTokens = {
  "--text-primary": { light: "#0F172A", dark: "#F8FAFC" },
  "--text-secondary": { light: "#475569", dark: "#94A3B8" },
  "--text-muted": { light: "#94A3B8", dark: "#64748B" },
  "--text-inverse": { light: "#FFFFFF", dark: "#0F172A" }
};

// Apply to text component
text.fills = [{
  type: 'SOLID',
  color: { type: 'VARIABLE_ALIAS', id: textPrimaryVar.id }
}];
```

---

## Text Component Properties

### Recommended Properties
```javascript
// Add these properties to text components
component.addComponentProperty("Content", 'TEXT', "Default Text");

// Optional: Add color property
component.addComponentProperty("Color", 'VARIANT', "Primary", {
  variantOptions: ['Primary', 'Secondary', 'Muted', 'Inverse']
});
```

---

## Best Practices

### ✅ DO
- Create text components for each semantic level (H1-H4, Body, Label, Caption)
- Bind font size, weight, and color to variables
- Add `Content` text property for easy overrides
- Set appropriate line heights per style
- Use `textAutoResize: 'WIDTH_AND_HEIGHT'` for most text

### ❌ DON'T
- Don't hardcode font sizes - use variables
- Don't mix font families in one system
- Don't forget line height - it affects readability
- Don't create too many text variants - keep it semantic

---

## Summary

Text components give you:
1. **Centralized control** over typography
2. **Variable binding** for theming
3. **Autolayout options** (hug vs fill)
4. **Content overrides** via component properties
5. **Consistency** across the design system

Use them when you want strict control over typography - which is most design systems!
