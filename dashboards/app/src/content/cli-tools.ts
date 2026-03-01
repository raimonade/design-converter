export interface CLITool {
  id: string;
  name: string;
  script: string;
  description: string;
  examples: string[];
  category: 'tokens' | 'analysis' | 'workflow' | 'testing' | 'conversion';
}

export const cliTools: CLITool[] = [
  {
    id: 'figma-tokens',
    name: 'Figma Tokens',
    script: 'figma-tokens.sh',
    description: 'Extract design tokens from Figma files. Export to CSS, JSON, or Tailwind config.',
    examples: [
      'figma-tokens.sh --preset=shadcn --export=css',
      'figma-tokens.sh --format=json --output ./tokens',
    ],
    category: 'tokens',
  },
  {
    id: 'figma-analyze',
    name: 'Figma Analyze',
    script: 'figma-analyze.sh',
    description: 'Analyze Figma files for colors, typography, and component patterns.',
    examples: [
      'figma-analyze.sh --type=colors --json',
      'figma-analyze.sh --type=typography --format=markdown',
    ],
    category: 'analysis',
  },
  {
    id: 'figma-workflow',
    name: 'Figma Workflow Runner',
    script: 'figma-workflow-runner.sh',
    description: 'Run predefined design workflows for automation.',
    examples: [
      'figma-workflow-runner.sh design-system',
      'figma-workflow-runner.sh --list',
    ],
    category: 'workflow',
  },
  {
    id: 'figma-smoke-test',
    name: 'Figma Smoke Test',
    script: 'figma-smoke-test.sh',
    description: 'End-to-end test suite for Figma MCP connections.',
    examples: [
      'figma-smoke-test.sh --quick',
      'figma-smoke-test.sh --verbose',
    ],
    category: 'testing',
  },
  {
    id: 'design-convert',
    name: 'Design Convert',
    script: 'design-convert.sh',
    description: 'Convert designs between Figma, Paper, and Pencil.dev formats.',
    examples: [
      'design-convert.sh figma:ABC123 paper:',
      'design-convert.sh pencil: figma: --figma-mode=http',
      'design-convert.sh --export-tokens tokens.json',
    ],
    category: 'conversion',
  },
  {
    id: 'figma-bridge',
    name: 'Figma Bridge Server',
    script: 'figma-bridge-server',
    description: 'HTTP bridge server for Figma plugin communication.',
    examples: [
      'figma-bridge-server --daemon',
      'figma-bridge-server --status',
    ],
    category: 'workflow',
  },
];

export const toolCategories = [
  { id: 'tokens', label: 'Tokens', count: cliTools.filter(t => t.category === 'tokens').length },
  { id: 'analysis', label: 'Analysis', count: cliTools.filter(t => t.category === 'analysis').length },
  { id: 'workflow', label: 'Workflow', count: cliTools.filter(t => t.category === 'workflow').length },
  { id: 'testing', label: 'Testing', count: cliTools.filter(t => t.category === 'testing').length },
  { id: 'conversion', label: 'Conversion', count: cliTools.filter(t => t.category === 'conversion').length },
];
