export interface LanguageMetric {
  language: string;
  component: string;
  linesOfCode: number;
  files: number;
  dependencies: string;
  purpose: string;
}

export const languageMetrics: LanguageMetric[] = [
  {
    language: 'TypeScript',
    component: 'figma-console MCP',
    linesOfCode: 27943,
    files: 42,
    dependencies: '11 runtime + 14 dev',
    purpose: 'Protocol layer — 56+ tools, WebSocket bridge, Cloudflare Workers',
  },
  {
    language: 'TypeScript',
    component: 'claude-talk-to-figma MCP',
    linesOfCode: 5258,
    files: 20,
    dependencies: 'MCP SDK + ws',
    purpose: 'Protocol layer — Claude-optimized, accessibility audits',
  },
  {
    language: 'Python',
    component: 'design-converter',
    linesOfCode: 19836,
    files: 32,
    dependencies: '0 runtime (stdlib only)',
    purpose: 'Transformation layer — IR, adapters, code generation',
  },
  {
    language: 'Bash',
    component: 'CLI tools',
    linesOfCode: 57000,
    files: 6,
    dependencies: 'curl, jq',
    purpose: 'Orchestration layer — workflows, automation',
  },
];

export interface ArchitectureLayer {
  name: string;
  languages: string[];
  components: string[];
  principle: string;
}

export const architectureLayers: ArchitectureLayer[] = [
  {
    name: 'Protocol Layer',
    languages: ['TypeScript'],
    components: ['figma-console MCP', 'claude-talk-to-figma MCP', 'official Figma MCP'],
    principle: 'MCP SDK is TypeScript-native. Long-lived servers with WebSocket. Zod schemas for tool validation.',
  },
  {
    name: 'Transformation Layer',
    languages: ['Python'],
    components: ['design-converter service', 'UNNode IR', 'adapters (figma/paper/pencil)'],
    principle: 'Zero external dependencies. Dataclasses for IR tree. F-strings for code generation. Network I/O bound, not CPU.',
  },
  {
    name: 'Orchestration Layer',
    languages: ['Bash'],
    components: ['figma-tokens.sh', 'figma-analyze.sh', 'design-convert.sh', 'figma-smoke-test.sh'],
    principle: 'CLI interface for all tools. Composable, scriptable, follows Unix philosophy.',
  },
];

export const designConverterStats = {
  linesOfCode: 19836,
  files: 32,
  runtimeDependencies: 0,
  testCount: 146,
  adapters: 3,
  irDataclasses: 15,
  irEnums: 13,
};

export const zeroDependencyModules = [
  'dataclasses', 'typing', 'enum', 'pathlib', 'json', 're', 'os', 'sys',
  'argparse', 'textwrap', 'abc', 'collections', 'http', 'urllib', 'socket',
  'struct', 'hashlib', 'asyncio', 'threading', 'subprocess', 'uuid',
  'signal', 'base64', 'copy', 'io', 'math',
];
