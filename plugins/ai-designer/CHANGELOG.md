# Changelog

All notable changes to this Figma design system will be documented in this file.

## [Unreleased]

## [1.0.0] - 2026-02-16

### Added
- **Variable Collection**: "Design System V1"
  - Single collection with all variables
  - Light and Dark modes

- **Primitives (30 variables)**
  - Colors: slate-50 through slate-950 (11), blue-500/600/700, white, black
  - Spacing: 0, 1(4px), 2(8px), 3(12px), 4(16px), 6(24px), 8(32px)
  - Radius: sm(4), md(8), lg(12)
  - FontSize: sm(14), base(16), lg(18), 2xl(24)

- **Semantic Colors (10 variables)**
  - background, foreground, foreground-secondary, foreground-muted
  - primary, primary-hover, primary-foreground
  - border, input-background, input-placeholder

- **Semantic Spacing & Gap (8 variables)**
  - padding: xs, sm, md, lg, xl
  - gap: xs, sm, md

- **Semantic Font Weight (4 variables)**
  - weight: regular(400), medium(500), semibold(600), bold(700)

- **Page Structure**
  - Index page with navigation and overview
  - Atoms page with components
  - Molecules page with compound components
  - Organisms page (in progress)

- **Components Created**
  - **Atoms**: Button (with TEXT slot), Button/Secondary, Input (with placeholder slot), Badge, Badge/Success, Badge/Warning
  - **Molecules**: Card (with title/description slots), Form Field (with label/placeholder/helperText slots), Navigation Item, Navigation Item/Active

### Fixed
- Font loading issue: Use "Inter" with "Semi Bold" (space, not camelCase)
- Component slot default values: BOOLEAN must be false, not null
- Variable alias creation: Now using createVariableAlias() + setValueForMode()
- Component variable binding: Using setBoundVariableForPaint for fills
- Auto-layout: All components now properly configured with layoutMode, primaryAxisSizingMode, counterAxisSizingMode, itemSpacing, and padding

## Known Limitations

- Variable aliases must be created manually in Figma (MCP limitation)
- MCP may show stale cache - always verify in Figma directly

---
*Built with Figma Console MCP*
