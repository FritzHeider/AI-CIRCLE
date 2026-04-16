// AgentHub — shared TypeScript types

// ── Enums ──────────────────────────────────────────────────────────────────

export type MessageType =
  | 'chat'
  | 'message'
  | 'system'
  | 'typing'
  | 'presence'
  | 'cost_update'
  | 'error'
  | 'pong'
  | 'history'
  | 'ping'
  | 'typing_start'
  | 'typing_stop'
  | 'join'
  | 'leave';

export type MessageRole = 'user' | 'assistant' | 'system';

export type AgentStatus = 'online' | 'offline' | 'typing';

// ── Core entities ──────────────────────────────────────────────────────────

export interface ArtifactInfo {
  type: 'code' | 'image' | 'markdown';
  language?: string;
  content?: string;
  url?: string;
  filename?: string;
}

export interface CostInfo {
  agent_id: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  session_total_usd: number;
  session_budget_usd: number;
  budget_pct: number;
}

export interface PresenceInfo {
  agent_id: string;
  agent_name: string;
  status: AgentStatus;
}

export interface WSMessage {
  id: string;
  type: MessageType;
  session_id: string;
  sender_id: string;
  sender_name: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  mentions: string[];
  artifacts: ArtifactInfo[];
  cost?: CostInfo;
  presence?: PresenceInfo;
  metadata: Record<string, unknown>;
  reply_to?: string;
}

// ── Agent ──────────────────────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  adapter_type: string;
  description: string;
  capabilities: string[];
  avatar_color: string;
  priority: number;
  enabled: boolean;
  system_prompt_override?: string;
  model_override?: string;
  hourly_cap_usd?: number;
  extra_config: Record<string, unknown>;
}

export interface AgentCreate {
  name: string;
  adapter_type: string;
  description?: string;
  capabilities?: string[];
  avatar_color?: string;
  priority?: number;
  enabled?: boolean;
  system_prompt_override?: string;
  model_override?: string;
  hourly_cap_usd?: number;
  extra_config?: Record<string, unknown>;
}

// ── Session ────────────────────────────────────────────────────────────────

export interface Session {
  id: string;
  name: string;
  description: string;
  budget_usd: number;
  created_at: string;
  updated_at?: string;
}

export interface SessionCreate {
  name: string;
  description?: string;
  budget_usd?: number;
}

// ── Cost ───────────────────────────────────────────────────────────────────

export interface AgentCostSummary {
  agent_id: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
}

export interface SessionCostSummary {
  session_id: string;
  total_usd: number;
  budget_usd: number;
  budget_pct: number;
  agents: AgentCostSummary[];
}

// ── Memory ─────────────────────────────────────────────────────────────────

export type SharedMemory = Record<string, unknown>;
export type PrivateMemory = Record<string, unknown>;

// ── Workflow ───────────────────────────────────────────────────────────────

export interface WorkflowNode {
  id: string;
  type: 'agent' | 'trigger' | 'condition' | 'output';
  agent_id?: string;
  label: string;
  config: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  trigger: 'manual' | 'scheduled' | 'event';
  trigger_config: Record<string, unknown>;
  created_at: string;
}
