# Figma Plugin API - Quick Reference

> Essential API for design generation - 2026-02-12

---

## 1. Creating Elements

```typescript
// Frame
const frame = figma.createFrame();
frame.resize(200, 100);
frame.layoutMode = 'VERTICAL';

// Rectangle
const rect = figma.createRectangle();
rect.fills = [{ type: 'SOLID', color: { r: 1, g: 0, b: 0 } }];

// Text (must load font first)
await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });
const text = figma.createText();
text.characters = "Hello";
text.fontSize = 16;
```

---

## 2. Auto-Layout

```typescript
frame.layoutMode = 'HORIZONTAL' | 'VERTICAL';
frame.primaryAxisSizingMode = 'AUTO' | 'FIXED';
frame.counterAxisSizingMode = 'AUTO' | 'FIXED';
frame.paddingLeft = 16;
frame.paddingRight = 16;
frame.itemSpacing = 8;
frame.primaryAxisAlignItems = 'CENTER';
frame.counterAxisAlignItems = 'CENTER';
```

---

## 3. Components

```typescript
// Create component
const component = figma.createComponent();
component.name = 'Button';

// From existing node
const component = figma.createComponentFromNode(frame);

// Create instance
const instance = component.createInstance();
```

---

## 4. Component Properties

```typescript
// Add text property
component.addComponentProperty("Label", 'TEXT', "Button");

// Add boolean property
component.addComponentProperty("Show Icon", 'BOOLEAN', true);

// Set on instance
instance.setProperties({
  "Label": "Click Me",
  "Show Icon": false
});
```

---

## 5. Best Practices

- **Load fonts first**: `await figma.loadFontAsync()`
- **Batch operations**: Create all, then configure
- **Undo points**: `figma.commitUndo()` after changes
- **Error handling**: Wrap in try/catch

---

Sources: [Figma Plugin API](https://developers.figma.com/docs/plugins/)
