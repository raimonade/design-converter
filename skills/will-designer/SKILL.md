---
name: will-designer
description: Design-specialized agent. Select with `@will-designer` or auto-routed by Will. Generates design systems with styles, colors, typography.
license: MIT
compatibility: OpenCode
metadata:
  author: william
  version: "1.0.0"
  type: specialized_agent
  parent: will
---

# Will Designer Skill

**Selectable specialized agent** - NOT a replacement for Will. Use `@will-designer` to select directly.

## Activation Triggers

```
design, UI, UX, landing page, dashboard, color, palette,
typography, font, style, layout, responsive, component,
theme, dark mode, light mode, branding, visual, aesthetic,
build a page, create a UI, make it look
```

## Quick Reference

### Style → Industry Matrix

| Industry | Primary Style | Alt Style | Avoid |
|----------|---------------|-----------|-------|
| SaaS | Minimalism | Glassmorphism | Brutalism |
| Fintech | Glassmorphism | Dark Mode | Neon, playful |
| Healthcare | Soft UI | Minimalism | Dark default |
| E-commerce | Bento Grid | Soft UI | Brutalism |
| Creative | Brutalism | Aurora | Corporate |
| Wellness | Neumorphism | Soft UI | High contrast |
| Gaming | Dark Mode | Cyberpunk | Light themes |
| Enterprise | Minimalism | Soft UI | Playful |
| Portfolio | Minimalism | Editorial | Cluttered |
| Education | Claymorphism | Soft UI | Dark default |

### Color Selection (30s Decision)

```
SaaS?        → #3B82F6 blue + #10B981 green
Fintech?     → #1E40AF navy + #059669 green
Healthcare?  → #0EA5E9 cyan + #22C55E green
E-commerce?  → #7C3AED purple + #EC4899 pink
Creative?    → #8B5CF6 purple + #EC4899 pink (dark bg)
Wellness?    → #059669 green + #8B5CF6 purple
Gaming?      → #8B5CF6 purple + #06B6D4 cyan (dark bg)
Enterprise?  → #1E3A5F navy + #0369A1 blue
```

### Typography (15s Decision)

```
Modern/Clean?    → Inter / Inter
Elegant/Luxury?  → Playfair Display / Source Serif Pro
Tech/Startup?    → Space Grotesk / DM Sans
Friendly/Warm?   → Nunito / Nunito Sans
Bold/Confident?  → Outfit / Outfit
```

### Layout Patterns

| Page Type | Structure |
|-----------|-----------|
| Landing | Hero → Features → Social Proof → CTA |
| Dashboard | Sidebar → Header → Content → Actions |
| Portfolio | Hero → Grid → About → Contact |
| E-commerce | Hero → Categories → Featured → Trust |

## Anti-Pattern Checklist

Before delivery, verify:

- [ ] No emoji as icons (use Lucide/Heroicons)
- [ ] `cursor: pointer` on all clickable
- [ ] Hover states (150-300ms transitions)
- [ ] Text contrast ≥ 4.5:1
- [ ] Focus states visible
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px

```

## ui-ux-pro-max Integration

**Full design system generator (67 styles, 96 palettes, 57 fonts):**

```bash
# Generate complete design system
python3 ~/.config/opencode/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system -p "Project"

# Domain searches
--domain style      # UI styles (glassmorphism, minimalism, etc.)
--domain color      # Color palettes by industry
--domain typography  # Font pairings
--domain landing    # Page structure patterns
--domain chart      # Chart types for dashboards

# Stack-specific
--stack react       # React guidelines
--stack nextjs      # Next.js guidelines
--stack swiftui     # SwiftUI guidelines
```

**Data Files Available:**
- `styles.csv` (67 styles)
- `colors.csv` (96 palettes)
- `typography.csv` (57 pairings)
- `ui-reasoning.csv` (100 industry rules)
- `ux-guidelines.csv` (99 guidelines)

## Usage

Or explicitly: `@will-designer Build a fintech app`
