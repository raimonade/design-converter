# Preact UI - Archived

**Status**: Archived (2026-02-20)
**Reason**: Build system uses `src/ui/index.html` (vanilla HTML), not Preact components.

## What This Contains

| File | Lines | Purpose |
|------|-------|---------|
| `App.tsx` | 203 | Root component with state management |
| `main.tsx` | 10 | Preact entry point |
| `styles.css` | 582 | Tailwind CSS styles |
| `components/PromptInput.tsx` | 33 | Textarea with character count |
| `components/ModelSelector.tsx` | 35 | Model toggle (GLM/Kimi/Auto) |
| `components/HistoryPanel.tsx` | 65 | Previous generations panel |
| `components/SettingsModal.tsx` | 101 | API key management |
| `components/PreviewPanel.tsx` | 33 | Design preview (never integrated) |
| `services/ai-service.ts` | 209 | AI request handling |

## Why Archived

The build configuration (`vite.config.ui.ts`) uses `src/ui/index.html` as entry point - a self-contained 1714-line vanilla HTML file. Preact components were never imported and existed as dead code.

## Active UI Features Missing from Preact

- Services Status Panel (Ollama + Proxy)
- 11 Preset Design Templates
- MiniMax M2.5 model option
- Keyboard shortcuts (Cmd+Enter, Cmd+K, Cmd+,, Esc)
- Error retry functionality
- Collapsible services panel

## To Restore/Integrate

1. Create `src/ui/index-preact.html`:
   ```html
   <!DOCTYPE html>
   <html>
   <body>
     <div id="app"></div>
     <script type="module" src="./main.tsx"></script>
   </body>
   </html>
   ```

2. Update `vite.config.ui.ts`:
   ```typescript
   rollupOptions: {
     input: resolve(__dirname, "src/ui/index-preact.html"),
   }
   ```

3. Port missing features from `src/ui/index.html`

4. Test Figma CSP compatibility

## Dependencies Required

```json
{
  "preact": "^10.25.4",
  "clsx": "^2.1.1",
  "@preact/preset-vite": "^2.10.2"
}
```

Already in `package.json` - no additional installation needed.
