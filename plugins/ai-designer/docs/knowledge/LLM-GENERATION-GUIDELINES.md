# LLM Design Generation Guidelines

> Comprehensive guide for AI-generated Figma designs

---

## Phase 1: Token First

**ALWAYS create tokens before components:**

```javascript
// Create collection
const collection = figma.variables.createVariableCollection("Theme");

// Define tokens (including typography!)
const tokens = {
  // Colors
  "color/primary": "#3B82F6",
  "color/background": "#FFFFFF",
  "color/text-primary": "#0F172A",
  
  // Typography
  "font-size-xl": 20,
  "font-size-2xl": 24,
  "font-weight-bold": "700",
  "line-height-tight": 1.25,
  
  // Spacing
  "spacing/md": 16
};

// Create variables
for (const [name, value] of Object.entries(tokens)) {
  const type = name.startsWith("color/") ? "COLOR" : 
               name.startsWith("font-size") || name.startsWith("spacing") ? "FLOAT" : "STRING";
  const variable = figma.variables.createVariable(name, collection, type);
  variable.setValueForMode(collection.modes[0].modeId, value);
}
```

---

## Phase 2: Build Text Components

**Create Text components FIRST (before other atoms):**

```javascript
async function createTextComponents() {
  const textStyles = [
    { name: 'Heading/1', size: 48, weight: 'Bold' },
    { name: 'Heading/2', size: 36, weight: 'Bold' },
    { name: 'Heading/3', size: 24, weight: 'SemiBold' },
    { name: 'Body/Default', size: 16, weight: 'Regular' },
    { name: 'Body/Small', size: 14, weight: 'Regular' },
    { name: 'Label/Default', size: 14, weight: 'Medium' },
    { name: 'Caption', size: 12, weight: 'Regular' }
  ];
  
  for (const style of textStyles) {
    await figma.loadFontAsync({ family: 'Inter', style: style.weight });
    const text = figma.createText();
    text.characters = style.name;
    text.fontSize = style.size;
    text.fontName = { family: 'Inter', style: style.weight };
    text.textAutoResize = 'WIDTH_AND_HEIGHT';
    
    const component = figma.createComponentFromNode(text);
    component.name = `Text/${style.name}`;
    component.addComponentProperty("Content", 'TEXT', style.name);
  }
}
```

---

## Phase 3: Build Other Components

### Button Template
```javascript
async function createButton() {
  const frame = figma.createFrame();
  frame.layoutMode = 'HORIZONTAL';
  frame.primaryAxisSizingMode = 'HUG';
  frame.counterAxisSizingMode = 'HUG';
  frame.paddingLeft = 16;
  frame.paddingRight = 16;
  frame.primaryAxisAlignItems = 'CENTER';
  frame.counterAxisAlignItems = 'CENTER';
  frame.cornerRadius = 6;
  
  // Bind to variable
  frame.fills = [{ type: 'SOLID', color: { type: 'VARIABLE_ALIAS', id: primaryVar.id } }];
  
  // Use Text component ref instead of inline text
  const textRef = textLabelComponent.createInstance();
  textRef.setProperties({ "Content": "Button" });
  frame.appendChild(textRef);
  
  return figma.createComponentFromNode(frame);
}
```

### Card Template (Using Text Refs)
```javascript
async function createCard() {
  const card = figma.createFrame();
  card.layoutMode = 'VERTICAL';
  card.itemSpacing = 12;
  card.padding = 24;
  card.cornerRadius = 12;
  
  // Title - use Text/Heading/3 ref
  const title = heading3Component.createInstance();
  title.setProperties({ "Content": "Card Title" });
  card.appendChild(title);
  
  // Body - use Text/Body/Default ref
  const body = bodyDefaultComponent.createInstance();
  body.setProperties({ "Content": "Description text here..." });
  card.appendChild(body);
  
  return figma.createComponentFromNode(card);
}
```

---

## Critical Rules

### ALWAYS
- Create typography tokens (size, weight, line-height)
- Create Text components before other atoms
- Use semantic tokens (never hardcode colors/sizes)
- Hug contents (primaryAxisSizingMode: 'HUG')
- Use Text refs in molecules/organisms
- Add component properties for content

### NEVER
- Hardcode hex values or font sizes
- Use fixed dimensions on main frames
- Create inline duplicates (use refs)
- Skip line height on text

---

## Quality Checklist

- [ ] Typography tokens defined
- [ ] Text components created (H1-H4, Body, Label, Caption)
- [ ] Text components have Content property
- [ ] Other components use Text refs
- [ ] Color tokens bound to variables
- [ ] Components reusable
- [ ] Auto-layout correct (hug, center, gap)

---

## Component Generation Order

```
1. Tokens (colors, typography, spacing)
2. Text Components (Heading, Body, Label, Caption)
3. Other Atoms (Button, Input, Badge)
4. Molecules (InputGroup, ListItem)
5. Organisms (Card, Sidebar)
```
