# Figma Variables System - Complete Reference

> Research compiled for AI Designer Plugin - 2026-02-12

---

## 1. What are Figma Variables?

Variables store reusable values that can be applied to design properties. They're like CSS variables or design tokens.

**Key Characteristics:**
- Stored in **collections** (folders)
- Support **modes** for multiple values (light/dark themes)
- Can be **bound** to node properties
- Changes propagate automatically

---

## 2. Variable Types

| Type | Use Cases | Value Format |
|------|-----------|--------------|
| **COLOR** | Backgrounds, text, strokes | `{r: 1, g: 0.5, b: 0, a: 1}` |
| **FLOAT** | Spacing, sizing, opacity, radius | Numbers (`16`, `24`) |
| **STRING** | Font families, icon names | Text (`"Inter"`) |
| **BOOLEAN** | Toggle states, visibility | `true` or `false` |

---

## 3. Plugin API Functions

```javascript
// Get collections
const collections = await figma.variables.getLocalVariableCollectionsAsync();

// Create collection
const collection = figma.variables.createVariableCollection("Theme");

// Create variable
const variable = figma.variables.createVariable("color/primary", collection, "COLOR");

// Set value for mode
variable.setValueForMode(modeId, { r: 0.23, g: 0.51, b: 0.96, a: 1 });

// Bind to node
node.setBoundVariable('fills', variable);
```

---

## 4. Naming Convention

```
[purpose]/[category]/[specific role]

Examples:
- color/bg/default
- color/text/primary
- spacing/md
- radius/small
```

---

## 5. Theme Modes

```javascript
// Create modes
const collection = figma.variables.createVariableCollection("Theme");
const lightModeId = collection.modes[0].modeId;
collection.renameMode(lightModeId, "Light");
const darkModeId = collection.addMode("Dark");

// Set values per mode
const bgVar = figma.variables.createVariable("color/bg", collection, "COLOR");
bgVar.setValueForMode(lightModeId, { r: 1, g: 1, b: 1, a: 1 });  // White
bgVar.setValueForMode(darkModeId, { r: 0.1, g: 0.1, b: 0.1, a: 1 });  // Dark
```

---

Sources: [Figma Plugin API](https://developers.figma.com/docs/plugins/working-with-variables/)
