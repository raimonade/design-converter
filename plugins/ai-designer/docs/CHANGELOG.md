# Changelog - Figma AI Designer Plugin

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-02-12

### Added
- Initial plugin structure with Vite + vanilla JS
- Dark theme UI matching modern design standards
- Multi-model support (GLM-5, GPT-4o-mini, Kimi 2.5)
- API key management via `figma.clientStorage`
- Settings modal for API configuration
- Design generation from text prompts
- Loading states and error handling

### Changed
- **BREAKING**: Switched from Preact to vanilla JS (Preact causes sandbox issues in Figma)
- Migrated from regular Z.AI API to Coding Plan endpoint

### Fixed
- Content Security Policy (CSP) blocking API calls
  - Added `https://open.bigmodel.cn` to `allowedDomains`
  - Added `https://api.openai.com` to `allowedDomains`
- API key storage now persists across sessions
- Button click handlers now work correctly

### Technical Details

#### Z.AI Coding Plan Discovery
- **Problem**: Regular Z.AI API (`api.z.ai`) requires credits - user has none
- **Solution**: Found Coding Plan endpoint (`open.bigmodel.cn`) that works with subscription
- **Key location**: `~/.local/share/opencode/auth.json` → `zai-coding-plan.key`

#### Architecture Decisions
1. **Vite + Vanilla JS**: Preact's JSX transformation conflicts with Figma's sandbox
2. **Inline Styles**: CSS modules don't work well in Figma plugin context
3. **Direct API Calls**: Using `fetch()` directly instead of SDKs for simplicity

#### File Structure
```
figma-ai-designer/
├── manifest.json          # Plugin config with CSP domains
├── src/
│   ├── plugin/
│   │   └── code.ts        # Main plugin logic
│   └── ui/
│       ├── index.html     # Plugin UI
│       ├── main.ts        # UI logic
│       └── style.css      # Styles
├── dist/                  # Built files
│   ├── code.js
│   └── ui.html
└── docs/
    ├── CHANGELOG.md       # This file
    └── SOUL.md            # Agent memory
```

### API Endpoints Used
| Provider | Endpoint | Model |
|----------|----------|-------|
| Z.AI Coding Plan | `https://open.bigmodel.cn/api/coding/paas/v4/chat/completions` | `glm-5` |
| OpenAI | `https://api.openai.com/v1/chat/completions` | `gpt-4o-mini` |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1/chat/completions` | `kimi-2.5` |

### Next Steps
- [ ] Test end-to-end design generation
- [ ] Add image generation support
- [ ] Implement design history
- [ ] Add export options

---

## Research Phase (Pre-0.1.0)

### Aesthetron AI Analysis
- Reverse-engineered architecture: Vite + Preact
- Uses Claude AND GPT for generation
- Found API endpoints and authentication flow
- Identified key features to replicate

### Market Research
- Competitor: Aesthetron AI (paid, closed-source)
- Opportunity: Open-source alternative using user's existing subscriptions
- Target: Users with Z.AI Coding Plan or OpenAI subscriptions
