export interface MCPServer {
  id: string;
  name: string;
  description: string;
  location: string;
  tools: number;
  capabilities: ('read' | 'write' | 'crud')[];
  protocol: string;
  status: 'active' | 'inactive' | 'pending';
}

export const mcpServers: MCPServer[] = [
  {
    id: 'figma-console',
    name: 'Figma Console',
    description: 'Full CRUD access to Figma via Desktop Bridge WebSocket. 56+ tools for complete design manipulation.',
    location: 'mcps/figma-console/',
    tools: 56,
    capabilities: ['read', 'write', 'crud'],
    protocol: 'WebSocket (9223-9232)',
    status: 'active',
  },
  {
    id: 'claude-talk-to-figma',
    name: 'Claude Talk to Figma',
    description: 'Claude-optimized MCP with accessibility audit tools and semantic design operations.',
    location: 'mcps/claude-talk-to-figma/',
    tools: 32,
    capabilities: ['read', 'write'],
    protocol: 'WebSocket + HTTP',
    status: 'active',
  },
  {
    id: 'official',
    name: 'Official Figma MCP',
    description: 'Official Figma MCP server with read-only access and Dev Mode integration.',
    location: 'mcps/official/',
    tools: 12,
    capabilities: ['read'],
    protocol: 'REST API',
    status: 'active',
  },
  {
    id: 'paper',
    name: 'Paper Design MCP',
    description: 'HTTP SSE JSON-RPC interface to Paper Design System on localhost:29979.',
    location: 'localhost:29979',
    tools: 24,
    capabilities: ['read', 'write', 'crud'],
    protocol: 'HTTP SSE (29979)',
    status: 'active',
  },
  {
    id: 'pencil',
    name: 'Pencil.dev MCP',
    description: 'Binary MCP server for .pen file editing. Supports stdio and HTTP modes.',
    location: '~/.cursor/extensions/highagency.pencildev-0.6.28/',
    tools: 18,
    capabilities: ['read', 'write', 'crud'],
    protocol: 'stdio / HTTP (19000-19009)',
    status: 'active',
  },
];

export const mcpStats = {
  total: mcpServers.length,
  active: mcpServers.filter(s => s.status === 'active').length,
  totalTools: mcpServers.reduce((sum, s) => sum + s.tools, 0),
};
