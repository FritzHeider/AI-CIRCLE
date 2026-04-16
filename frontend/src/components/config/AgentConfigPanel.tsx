import React, { useState } from 'react';
import { api } from '../../lib/api';
import type { Agent, AgentCreate } from '../../types';
import { useAgents } from '../../hooks/useAgents';

const ADAPTER_TYPES = ['claude', 'openai', 'gemini', 'falai', 'human'];
const AVATAR_COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const BLANK_FORM: AgentCreate = {
  name: '',
  adapter_type: 'claude',
  description: '',
  capabilities: [],
  avatar_color: '#6366f1',
  priority: 50,
  enabled: true,
};

export const AgentConfigPanel: React.FC = () => {
  const { agents, refetch } = useAgents();
  const [editingId, setEditingId] = useState<string | 'new' | null>(null);
  const [form, setForm] = useState<AgentCreate>(BLANK_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openNew = () => {
    setForm(BLANK_FORM);
    setEditingId('new');
    setError(null);
  };

  const openEdit = (agent: Agent) => {
    setForm({
      name: agent.name,
      adapter_type: agent.adapter_type,
      description: agent.description,
      capabilities: agent.capabilities,
      avatar_color: agent.avatar_color,
      priority: agent.priority,
      enabled: agent.enabled,
      system_prompt_override: agent.system_prompt_override,
      model_override: agent.model_override,
      hourly_cap_usd: agent.hourly_cap_usd,
    });
    setEditingId(agent.id);
    setError(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      if (editingId === 'new') {
        await api.agents.create(form);
      } else if (editingId) {
        await api.agents.update(editingId, form);
      }
      setEditingId(null);
      refetch();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this agent?')) return;
    try {
      await api.agents.delete(id);
      refetch();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : 'Delete failed');
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">Agent Configuration</h2>
        <button
          onClick={openNew}
          className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg"
        >
          + New Agent
        </button>
      </div>

      {/* Inline editor */}
      {editingId && (
        <div className="mb-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
          <h3 className="text-sm font-semibold mb-3 text-gray-700">
            {editingId === 'new' ? 'Create Agent' : 'Edit Agent'}
          </h3>
          <div className="space-y-2">
            <input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <select
              value={form.adapter_type}
              onChange={(e) => setForm({ ...form, adapter_type: e.target.value })}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none"
            >
              {ADAPTER_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input
              placeholder="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <input
              placeholder="Model override (e.g. claude-opus-4-6)"
              value={form.model_override ?? ''}
              onChange={(e) => setForm({ ...form, model_override: e.target.value || undefined })}
              className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <div className="flex gap-2 flex-wrap">
              {AVATAR_COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => setForm({ ...form, avatar_color: c })}
                  className={`w-6 h-6 rounded-full border-2 ${
                    form.avatar_color === c ? 'border-gray-800' : 'border-transparent'
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={100}
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: +e.target.value })}
                className="w-20 text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none"
              />
              <span className="text-xs text-gray-500">Priority (0=highest)</span>
              <label className="ml-auto flex items-center gap-1 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
                />
                Enabled
              </label>
            </div>

            {error && <p className="text-xs text-red-600">{error}</p>}

            <div className="flex gap-2 pt-1">
              <button
                onClick={handleSave}
                disabled={saving || !form.name}
                className="text-xs bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-1.5 rounded-lg"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={() => setEditingId(null)}
                className="text-xs text-gray-600 hover:text-gray-800 px-3 py-1.5"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Agent list */}
      <ul className="space-y-2">
        {agents.map((agent) => (
          <li
            key={agent.id}
            className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-3 py-2"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-medium flex-shrink-0"
                style={{ backgroundColor: agent.avatar_color }}
              >
                {agent.name[0]}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{agent.name}</p>
                <p className="text-xs text-gray-400">{agent.adapter_type}</p>
              </div>
            </div>
            <div className="flex gap-1 ml-2">
              <button
                onClick={() => openEdit(agent)}
                className="text-xs text-indigo-600 hover:text-indigo-800 px-2 py-1"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(agent.id)}
                className="text-xs text-red-500 hover:text-red-700 px-2 py-1"
              >
                Del
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
