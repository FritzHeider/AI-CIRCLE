// REST API client for AgentHub backend
import type {
  Agent, AgentCreate, Session, SessionCreate,
  SessionCostSummary, SharedMemory, Workflow, WSMessage,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Sessions ──────────────────────────────────────────────────────────────

export const api = {
  sessions: {
    list: (limit = 50, offset = 0) =>
      request<Session[]>(`/api/sessions?limit=${limit}&offset=${offset}`),
    create: (data: SessionCreate) =>
      request<Session>('/api/sessions', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) =>
      request<Session>(`/api/sessions/${id}`),
    update: (id: string, data: Partial<Session>) =>
      request<Session>(`/api/sessions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<void>(`/api/sessions/${id}`, { method: 'DELETE' }),
  },

  agents: {
    list: () => request<Agent[]>('/api/agents'),
    create: (data: AgentCreate) =>
      request<Agent>('/api/agents', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => request<Agent>(`/api/agents/${id}`),
    update: (id: string, data: Partial<Agent>) =>
      request<Agent>(`/api/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/api/agents/${id}`, { method: 'DELETE' }),
  },

  messages: {
    list: (sessionId: string, limit = 50, beforeId?: string) => {
      const qs = beforeId ? `?limit=${limit}&before_id=${beforeId}` : `?limit=${limit}`;
      return request<WSMessage[]>(`/api/messages/${sessionId}${qs}`);
    },
  },

  memory: {
    getShared: (sessionId: string) =>
      request<SharedMemory>(`/api/memory/shared/${sessionId}`),
    setShared: (sessionId: string, key: string, value: unknown, agentId?: string) =>
      request<{ ok: boolean }>(`/api/memory/shared/${sessionId}`, {
        method: 'PUT',
        body: JSON.stringify({ key, value, agent_id: agentId }),
      }),
    deleteShared: (sessionId: string, key: string) =>
      request<{ ok: boolean }>(`/api/memory/shared/${sessionId}/${key}`, { method: 'DELETE' }),
    getPrivate: (agentId: string, sessionId: string) =>
      request<Record<string, unknown>>(`/api/memory/private/${agentId}/${sessionId}`),
  },

  costs: {
    summary: (sessionId: string) =>
      request<SessionCostSummary>(`/api/costs/${sessionId}/summary`),
    getBudget: (sessionId: string) =>
      request<{ session_id: string; budget_usd: number }>(`/api/costs/${sessionId}/budget`),
    setBudget: (sessionId: string, budgetUsd: number) =>
      request<{ session_id: string; budget_usd: number }>(
        `/api/costs/${sessionId}/budget?budget_usd=${budgetUsd}`,
        { method: 'PUT' },
      ),
  },

  workflows: {
    list: () => request<Workflow[]>('/api/workflows'),
    create: (data: Partial<Workflow>) =>
      request<Workflow>('/api/workflows', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => request<Workflow>(`/api/workflows/${id}`),
    update: (id: string, data: Partial<Workflow>) =>
      request<Workflow>(`/api/workflows/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/api/workflows/${id}`, { method: 'DELETE' }),
    executionOrder: (id: string) =>
      request<{ workflow_id: string; execution_order: string[] }>(
        `/api/workflows/${id}/execution-order`,
      ),
  },
};
