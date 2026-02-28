# Token System - Complete Variable Architecture

> Full taxonomy of design tokens with primitive → semantic → component hierarchy

---

## 1. Token Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ LEVEL 3: COMPONENT TOKENS (Specific Use)                    │
│   --button-bg-primary, --input-border-focus                 │
├─────────────────────────────────────────────────────────────┤
│ LEVEL 2: SEMANTIC TOKENS (Purpose)                          │
│   --primary, --background, --text-primary, --border         │
├─────────────────────────────────────────────────────────────┤
│ LEVEL 1: PRIMITIVE TOKENS (Raw Values)                      │
│   --blue-500, --gray-100, --spacing-4, --radius-md          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Complete Token Taxonomy

### 2.1 Color Tokens

#### Primitive Colors (Base Palette)
```javascript
// Blue scale
--blue-50:   #eff6ff
--blue-100:  #dbeafe
--blue-200:  #bfdbfe
--blue-300:  #93c5fd
--blue-400:  #60a5fa
--blue-500:  #3b82f6
--blue-600:  #2563eb
--blue-700:  #1d4ed8
--blue-800:  #1e40af
--blue-900:  #1e3a8a

// Gray scale
--gray-50:   #f9fafb
--gray-100:  #f3f4f6
--gray-200:  #e5e7eb
--gray-300:  #d1d5db
--gray-400:  #9ca3af
--gray-500:  #6b7280
--gray-600:  #4b5563
--gray-700:  #374151
--gray-800:  #1f2937
--gray-900:  #111827

// Semantic color primitives
--green-500: #22c55e
--green-700: #15803d
--yellow-500: #eab308
--yellow-600: #ca8a04
--red-500:   #ef4444
--red-600:   #dc2626
--orange-500: #f97316
```

#### Semantic Colors (Purpose)
```javascript
// Brand
--primary:             $--blue-500
--primary-hover:       $--blue-600
--primary-foreground:  #ffffff

// Backgrounds
--background:          $--gray-50
--surface:             #ffffff
--surface-elevated:    #ffffff

// Foregrounds (text)
--foreground:          $--gray-900
--foreground-muted:    $--gray-500
--foreground-subtle:   $--gray-400

// Borders
--border:              $--gray-200
--border-subtle:       $--gray-100
--border-focus:        $--blue-500

// Semantic feedback
--success:             $--green-500
--success-foreground:  #ffffff
--warning:             $--yellow-500
--warning-foreground:  $--gray-900
--error:               $--red-500
--error-foreground:    #ffffff
--info:                $--blue-500
--info-foreground:     #ffffff

// Component-specific
--muted:               $--gray-100
--muted-foreground:    $--gray-500
--accent:              $--blue-500
--accent-foreground:   #ffffff
```

#### Component Colors (Specific Use)
```javascript
// Button
--button-bg:           $--primary
--button-bg-hover:     $--primary-hover
--button-text:         $--primary-foreground

// Input
--input-bg:            $--surface
--input-border:        $--border
--input-border-focus:  $--border-focus
--input-placeholder:   $--foreground-subtle

// Card
--card-bg:             $--surface
--card-border:         $--border
--card-text:           $--foreground

// Sidebar
--sidebar-bg:          $--surface
--sidebar-border:      $--border
--sidebar-text:        $--foreground
--sidebar-active:      $--primary
```

---

### 2.2 Dimension Tokens

#### Spacing (4px base)
```javascript
// Scale
--spacing-0:   0
--spacing-px:  1
--spacing-0.5: 2
--spacing-1:   4
--spacing-1.5: 6
--spacing-2:   8
--spacing-2.5: 10
--spacing-3:   12
--spacing-3.5: 14
--spacing-4:   16
--spacing-5:   20
--spacing-6:   24
--spacing-7:   28
--spacing-8:   32
--spacing-9:   36
--spacing-10:  40
--spacing-11:  44
--spacing-12:  48
--spacing-14:  56
--spacing-16:  64
--spacing-20:  80
--spacing-24:  96
--spacing-28:  112
--spacing-32:  128

// Semantic spacing
--gap-xs:   $--spacing-1
--gap-sm:   $--spacing-2
--gap-md:   $--spacing-4
--gap-lg:   $--spacing-6
--gap-xl:   $--spacing-8

--padding-xs:   $--spacing-1
--padding-sm:   $--spacing-2
--padding-md:   $--spacing-4
--padding-lg:   $--spacing-6
--padding-xl:   $--spacing-8
```

#### Sizing
```javascript
// Fixed sizes
--size-0:    0
--size-1:    4
--size-2:    8
--size-3:    12
--size-4:    16
--size-5:    20
--size-6:    24
--size-8:    32
--size-10:   40
--size-12:   48
--size-16:   64
--size-20:   80
--size-24:   96
--size-32:   128
--size-40:   160
--size-48:   192
--size-56:   224
--size-64:   256

// Component heights
--height-sm:  32
--height-md:  40
--height-lg:  48
--height-xl:  56

// Icon sizes
--icon-xs:  12
--icon-sm:  16
--icon-md:  20
--icon-lg:  24
--icon-xl:  32
```

---

### 2.3 Border Tokens

#### Border Width
```javascript
--border-0: 0
--border-1: 1
--border-2: 2
--border-4: 4
--border-8: 8
```

#### Border Radius
```javascript
// Scale
--radius-none: 0
--radius-sm:   4
--radius-md:   8
--radius-lg:   12
--radius-xl:   16
--radius-2xl:  24
--radius-3xl:  32
--radius-full: 9999

// Semantic
--radius-button:   $--radius-md
--radius-input:    $--radius-md
--radius-card:     $--radius-lg
--radius-modal:    $--radius-xl
--radius-avatar:   $--radius-full
--radius-badge:    $--radius-full
```

---

### 2.4 Effect Tokens

#### Shadows
```javascript
// Scale
--shadow-xs:   0 1px 2px 0 rgba(0,0,0,0.05)
--shadow-sm:   0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)
--shadow-md:   0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)
--shadow-lg:   0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)
--shadow-xl:   0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)
--shadow-2xl:  0 25px 50px -12px rgba(0,0,0,0.25)
--shadow-inner: inset 0 2px 4px 0 rgba(0,0,0,0.05)

// Semantic
--shadow-card:    $--shadow-sm
--shadow-modal:   $--shadow-xl
--shadow-dropdown: $--shadow-lg
--shadow-tooltip: $--shadow-md
```

#### Blur
```javascript
--blur-none: 0
--blur-sm:   4
--blur-md:   8
--blur-lg:   16
--blur-xl:   24
--blur-2xl:  40
--blur-3xl:  64
```

#### Opacity
```javascript
--opacity-0:    0
--opacity-5:    0.05
--opacity-10:   0.1
--opacity-15:   0.15
--opacity-20:   0.2
--opacity-25:   0.25
--opacity-30:   0.3
--opacity-40:   0.4
--opacity-50:   0.5
--opacity-60:   0.6
--opacity-70:   0.7
--opacity-75:   0.75
--opacity-80:   0.8
--opacity-90:   0.9
--opacity-95:   0.95
--opacity-100:  1

// Semantic
--opacity-disabled: $--opacity-50
--opacity-hover:    $--opacity-80
--opacity-backdrop: $--opacity-50
```

---

### 2.5 Typography Tokens

#### Font Family
```javascript
--font-sans:     "Inter", system-ui, -apple-system, sans-serif
--font-serif:    "Georgia", Cambria, serif
--font-mono:     "SF Mono", "Fira Code", monospace
--font-display:  "Inter", system-ui, sans-serif
```

#### Font Size
```javascript
// Scale
--text-xs:    12
--text-sm:    14
--text-base:  16
--text-lg:    18
--text-xl:    20
--text-2xl:   24
--text-3xl:   30
--text-4xl:   36
--text-5xl:   48
--text-6xl:   60
--text-7xl:   72
--text-8xl:   96
--text-9xl:   128

// Semantic
--text-caption:    $--text-xs
--text-label:      $--text-sm
--text-body:       $--text-base
--text-body-lg:    $--text-lg
--text-heading:    $--text-xl
--text-title:      $--text-2xl
--text-headline:   $--text-3xl
--text-display:    $--text-5xl
```

#### Font Weight
```javascript
--font-thin:       100
--font-extralight: 200
--font-light:      300
--font-normal:     400
--font-medium:     500
--font-semibold:   600
--font-bold:       700
--font-extrabold:  800
--font-black:      900
```

#### Line Height
```javascript
--leading-none:    1
--leading-tight:   1.25
--leading-snug:    1.375
--leading-normal:  1.5
--leading-relaxed: 1.625
--leading-loose:   2
```

#### Letter Spacing
```javascript
--tracking-tighter: -0.05em
--tracking-tight:   -0.025em
--tracking-normal:  0
--tracking-wide:    0.025em
--tracking-wider:   0.05em
--tracking-widest:  0.1em
```

---

### 2.6 Motion Tokens (Optional)

#### Duration
```javascript
--duration-75:    75ms
--duration-100:   100ms
--duration-150:   150ms
--duration-200:   200ms
--duration-300:   300ms
--duration-500:   500ms
--duration-700:   700ms
--duration-1000:  1000ms

// Semantic
--duration-fast:   $--duration-150
--duration-normal: $--duration-200
--duration-slow:   $--duration-300
```

#### Easing
```javascript
--ease-linear:      linear
--ease-in:          cubic-bezier(0.4, 0, 1, 1)
--ease-out:         cubic-bezier(0, 0, 0.2, 1)
--ease-in-out:      cubic-bezier(0.4, 0, 0.2, 1)
--ease-bounce:      cubic-bezier(0.68, -0.55, 0.265, 1.55)
```

---

## 3. Theme Modes

### Light/Dark Mode Structure
```javascript
const collection = figma.variables.createVariableCollection("Theme");
const lightMode = collection.modes[0].modeId;
collection.renameMode(lightMode, "Light");
const darkMode = collection.addMode("Dark");

// Define tokens with mode values
const bgVar = figma.variables.createVariable("--background", collection, "COLOR");
bgVar.setValueForMode(lightMode, { r: 0.98, g: 0.98, b: 0.98 });  // #fafafa
bgVar.setValueForMode(darkMode, { r: 0.06, g: 0.06, b: 0.06 });   // #0f0f0f
```

---

## 4. Figma Variable Implementation

```javascript
// Complete token creation
async function createTokenSystem() {
  const collection = figma.variables.createVariableCollection("Design Tokens");
  const modeId = collection.modes[0].modeId;
  
  const tokens = {
    // Colors
    "--primary": { type: "COLOR", value: { r: 0.23, g: 0.51, b: 0.96 } },
    "--background": { type: "COLOR", value: { r: 0.98, g: 0.98, b: 0.98 } },
    
    // Spacing
    "--spacing-4": { type: "FLOAT", value: 16 },
    "--spacing-6": { type: "FLOAT", value: 24 },
    
    // Radius
    "--radius-md": { type: "FLOAT", value: 8 },
    "--radius-lg": { type: "FLOAT", value: 12 },
    
    // Typography
    "--text-base": { type: "FLOAT", value: 16 },
    "--font-medium": { type: "FLOAT", value: 500 },
    
    // Effects
    "--opacity-50": { type: "FLOAT", value: 0.5 }
  };
  
  for (const [name, config] of Object.entries(tokens)) {
    const variable = figma.variables.createVariable(name, collection, config.type);
    variable.setValueForMode(modeId, config.value);
  }
  
  return collection;
}
```

---

## 5. Token Usage in Components

```javascript
// Using tokens in component creation
async function createButtonWithTokens() {
  const button = figma.createFrame();
  
  // Get tokens
  const primaryBg = await getVariable("--primary");
  const primaryFg = await getVariable("--primary-foreground");
  const spacing4 = await getVariable("--spacing-4");
  const radiusMd = await getVariable("--radius-md");
  
  // Apply tokens
  button.fills = [{
    type: 'SOLID',
    color: { type: 'VARIABLE_ALIAS', id: primaryBg.id }
  }];
  
  button.paddingLeft = 16;   // Maps to --spacing-4
  button.paddingRight = 16;
  button.paddingTop = 10;
  button.paddingBottom = 10;
  button.cornerRadius = 8;  // Maps to --radius-md
  
  return button;
}
```

---

## 6. Zero Values (Important!)

### Spacing-0 Variable
```javascript
// ALWAYS use spacing-0 instead of raw 0
--spacing-0: { type: "FLOAT", value: 0 }

// Usage examples
padding: "$--spacing-0"     // Instead of padding: 0
gap: "$--spacing-0"         // Instead of gap: 0
margin: "$--spacing-0"      // Instead of margin: 0
```

### Why Use spacing-0 Variable?

1. **Consistency** - All spacing uses the same variable pattern
2. **Intent clarity** - `$--spacing-0` vs `0` makes intent explicit
3. **Future flexibility** - Can add semantic meaning later
4. **Searchability** - Easy to find all zero-spacing usages

### Complete Zero Token Set
```javascript
// Zero values as variables
--spacing-0:   0     // No spacing
--size-0:      0     // No size
--radius-0:    0     // No radius (sharp corners)
--border-0:    0     // No border
--opacity-0:   0     // Fully transparent
--shadow-none: none  // No shadow
```

### When to Use Each Zero

| Token | Usage |
|-------|-------|
| `$--spacing-0` | padding, gap, margin = 0 |
| `$--size-0` | width, height = 0 |
| `$--radius-0` | cornerRadius = 0 (sharp) |
| `$--border-0` | strokeWidth = 0 |
| `$--opacity-0` | opacity = 0 (invisible) |

### Examples

```javascript
// Button with no gap
{
  "gap": "$--spacing-0",
  "padding": [10, 16]
}

// Divider line (no height, only border)
{
  "height": "$--size-0",
  "stroke": { "bottom": "$--border-1" }
}

// Sharp corners (no radius)
{
  "cornerRadius": "$--radius-0"
}
```
