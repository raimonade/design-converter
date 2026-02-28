# AI Designer - Figma Plugin

> Open-source AI-powered Figma design generator with multi-model support

## Features

- **Multi-Model AI Support**: Claude 3.5 Sonnet, Kimi 2.5, GPT-4o
- **Auto Mode**: AI automatically selects the best model for your prompt
- **Design System Integration**: Reads your local styles and variables
- **History**: Track and reuse previous generations
- **Open Source**: MIT licensed, fully transparent

## Quick Start

```bash
# Install dependencies
npm install

# Development (watch mode)
npm run dev

# Build for production
npm run build
```

## Configuration

Add your API keys in the plugin settings:

1. **Claude**: Get from [Anthropic Console](https://console.anthropic.com)
2. **Kimi**: Get from [Moonshot AI](https://platform.moonshot.cn)
3. **OpenAI**: Get from [OpenAI Platform](https://platform.openai.com)

## Architecture

```
src/
├── plugin/           # Figma plugin code (runs in sandbox)
│   └── code.ts       # Main plugin logic
├── ui/               # Plugin UI (Preact)
│   ├── App.tsx       # Main UI component
│   ├── components/   # UI components
│   ├── services/     # AI services
│   └── styles.css    # Tailwind-based styles
└── shared/           # Shared types
    └── types/
        └── messages.ts  # Message type definitions
```

## Comparison with Aesthetron AI

| Feature | Aesthetron AI | AI Designer |
|---------|---------------|-------------|
| Open Source | ❌ | ✅ MIT |
| BYOK | Paid add-on | ✅ Free |
| Local-First | ❌ | ✅ Optional |
| Model Choice | Fixed | ✅ 3+ models |
| Transparent Pricing | ❌ | ✅ |

## API Endpoints (For Self-Hosting)

```
POST /api/generate
  - prompt: string
  - mode: "claude" | "kimi" | "openai" | "auto"
  - context?: DesignContext
```

## License

MIT
