# SOUL.md - Figma AI Designer Plugin

## Project Identity

This is an **open-source Figma plugin** that generates designs from text prompts. It's built as an alternative to Aesthetron AI, using the user's existing AI subscriptions (Z.AI Coding Plan, OpenAI, NVIDIA NIM).

---

## Core Principles

### 1. User's Subscriptions First
- **ALWAYS** use Z.AI Coding Plan endpoint (`open.bigmodel.cn`), NOT regular API (`api.z.ai`)
- User has active Coding Plan subscription, no credits on regular API
- Fallback to OpenAI if Coding Plan unavailable

### 2. Figma Plugin Constraints
- **NO JSX/Preact**: Causes sandbox issues, use vanilla JS
- **CSP Compliance**: All API domains MUST be in `manifest.json` `allowedDomains`
- **Storage**: Use `figma.clientStorage` for persistence

### 3. Dark Theme UI
- Modern, clean interface
- Consistent with design tool aesthetics
- Accessible contrast ratios

---

## Technical Architecture

### Build System
```
Vite + TypeScript
├── vite.config.plugin.ts  → dist/code.js
└── vite.config.ui.ts      → dist/ui.html
```

### Key Files
| File | Purpose |
|------|---------|
| `manifest.json` | Plugin config + CSP domains |
| `src/plugin/code.ts` | Main plugin logic, API calls |
| `src/ui/index.html` | Plugin UI |
| `src/ui/main.ts` | UI event handlers |
| `src/ui/style.css` | Dark theme styles |

### API Configuration
```typescript
const config = mode === "glm" 
  ? { 
      url: "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions", 
      model: "glm-5" 
    }
  : { 
      url: "https://api.openai.com/v1/chat/completions", 
      model: "gpt-4o-mini" 
    };
```

---

## Known Issues & Solutions

### Issue 1: CSP Blocking API Calls
**Error**: `Please add "https://open.bigmodel.cn" to the networkAccess > allowedDomains`
**Solution**: Add domain to `manifest.json`:
```json
{
  "networkAccess": {
    "allowedDomains": [
      "https://open.bigmodel.cn",
      "https://api.openai.com",
      "https://integrate.api.nvidia.com"
    ]
  }
}
```

### Issue 2: Preact JSX Not Working
**Symptom**: Plugin fails to load or buttons don't work
**Solution**: Use vanilla JS with inline event handlers

### Issue 3: API Key Not Persisting
**Solution**: Use `figma.clientStorage.setAsync()` and `getAsync()`

---

## Development Workflow

### Build & Test
```bash
cd "/Users/william/Projects Parent Folder/figma-ai-designer"
npm run build
cp dist/index.html dist/ui.html
```

### Import to Figma
1. Open Figma Desktop
2. `Plugins > Development > Import plugin from manifest`
3. Select: `figma-ai-designer/manifest.json`

### Debug
- Check browser console in Figma (Developer Tools)
- Look for CSP errors in console
- Verify API key is set in Settings

---

## User Context

### User's Subscriptions
- **Z.AI Coding Plan**: Active (use `open.bigmodel.cn` endpoint)
- **OpenAI**: Available as fallback
- **NVIDIA NIM**: Kimi 2.5 available

### User's API Key
Location: `~/.local/share/opencode/auth.json`
```json
{
  "zai-coding-plan": {
    "type": "api",
    "key": "0fc788cb200c4f7685478d35fc4ac6a1.7mw2yptB3AeKPmb6"
  }
}
```

---

## Future Roadmap

### v0.2.0
- [ ] Image generation support
- [ ] Design history
- [ ] Export to code

### v0.3.0
- [ ] Component library integration
- [ ] Team collaboration
- [ ] Custom model fine-tuning

---

## Handoff Protocol

When continuing work on this project:

1. **Read this SOUL.md first** - Contains all context
2. **Check CHANGELOG.md** - Recent changes
3. **Verify manifest.json** - CSP domains must be current
4. **Test with user's key** - Coding Plan endpoint, not regular API

### Quick Start for New Agents
```
Project: Figma AI Designer Plugin
Location: /Users/william/Projects Parent Folder/figma-ai-designer/
Tech: Vite + TypeScript + Vanilla JS
Key Insight: Use Z.AI Coding Plan endpoint (open.bigmodel.cn)
Status: Ready to test in Figma
```
