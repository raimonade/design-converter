# Component & Variable Improvements Analysis

## Current Issues

### 1. Variables Not Bound to Components ❌
- Variables are created but components still use hardcoded colors
- No connection between semantic tokens and component fills

### 2. No Variable Aliasing ❌
- Semantic tokens duplicate primitive values instead of referencing them
- Should use `createVariableAlias()` for true token hierarchy

### 3. Component Properties Not Bound ❌
- Properties created but not connected to text content
- Boolean properties don't control layer visibility

### 4. Missing Typography Variables ❌
- No fontSize, fontWeight, lineHeight variables
- Text nodes use hardcoded values

### 5. No Dark Mode Support ❌
- Single mode in variable collection
- Should support Light/Dark modes

### 6. No Instance Creation ❌
- Can only create components, not instances
- Users can't quickly use created components

### 7. Missing Number Properties ❌
- No support for size, spacing overrides
- Components lack flexible numeric controls

## Figma API Capabilities We Should Use

### Variable Binding
```typescript
// Bind fill to variable
const variable = figma.variables.getVariableById(varId)
frame.fills = [{
  type: 'SOLID',
  boundVariables: { color: { type: 'VARIABLE_ALIAS', id: variable.id } }
}]
```

### Component Property Binding
```typescript
// Bind text to component property
textNode.boundVariables = {
  characters: { type: 'PROPERTY', key: 'label' }
}

// Bind visibility to boolean property
frame.boundVariables = {
  visible: { type: 'PROPERTY', key: 'showIcon' }
}
```

### Dark Mode
```typescript
const collection = figma.variables.createVariableCollection("Theme")
collection.addMode("Dark")
// Set values for each mode
variable.setValueForMode(lightModeId, lightValue)
variable.setValueForMode(darkModeId, darkValue)
```

### Number Properties
```typescript
component.addComponentProperty("Size", "NUMBER", 16)
```

