import React, { useState } from 'react';
import { ChatRoom } from './components/chat/ChatRoom';
import { CostDashboard } from './components/dashboard/CostDashboard';
import { AgentStatusPanel } from './components/dashboard/AgentStatusPanel';
import { AgentConfigPanel } from './components/config/AgentConfigPanel';
import { SessionHistory } from './components/dashboard/SessionHistory';
import { WorkflowBuilder } from './components/workflow/WorkflowBuilder';
import { useAgents } from './hooks/useAgents';

// Default human user identity
const HUMAN_AGENT_ID = 'fritz-human';
const HUMAN_AGENT_NAME = 'Fritz';

type View = 'chat' | 'dashboard' | 'agents' | 'workflows';

export default function App() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [view, setView] = useState<View>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { agents } = useAgents();

  const navItems: { id: View; label: string; icon: string }[] = [
    { id: 'chat',       label: 'Chat',      icon: '💬' },
    { id: 'dashboard',  label: 'Costs',     icon: '📊' },
    { id: 'agents',     label: 'Agents',    icon: '🤖' },
    { id: 'workflows',  label: 'Workflows', icon: '🔀' },
  ];

  return (
    <div className="flex h-screen bg-gray-100 text-gray-900 overflow-hidden">
      {/* ── Sidebar ──────────────────────────────────────────────── */}
      <aside
        className={`flex flex-col bg-white border-r border-gray-200 transition-all duration-200 ${
          sidebarOpen ? 'w-64' : 'w-14'
        }`}
      >
        {/* Logo / toggle */}
        <div className="flex items-center gap-2 px-4 py-4 border-b border-gray-100">
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="text-gray-400 hover:text-gray-600 text-lg"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
          {sidebarOpen && (
            <span className="font-bold text-indigo-600 text-lg">AgentHub</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-1 px-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                view === item.id
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {sidebarOpen && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Session list (only in chat view) */}
        {sidebarOpen && view === 'chat' && (
          <div className="border-t border-gray-100 overflow-y-auto max-h-64">
            <SessionHistory
              activeSessionId={activeSessionId}
              onSelectSession={setActiveSessionId}
            />
          </div>
        )}

        {/* Agent presence (bottom of sidebar) */}
        {sidebarOpen && (
          <div className="border-t border-gray-100 overflow-y-auto max-h-48">
            <AgentStatusPanel agents={agents} />
          </div>
        )}
      </aside>

      {/* ── Main content ─────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {view === 'chat' && (
          <>
            {activeSessionId ? (
              <ChatRoom
                sessionId={activeSessionId}
                currentAgentId={HUMAN_AGENT_ID}
                currentAgentName={HUMAN_AGENT_NAME}
                agents={agents}
              />
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
                <p className="text-5xl mb-4">🤝</p>
                <p className="text-xl font-semibold text-gray-600 mb-2">Welcome to AgentHub</p>
                <p className="text-sm">Select or create a session from the sidebar to begin.</p>
              </div>
            )}
          </>
        )}

        {view === 'dashboard' && activeSessionId && (
          <div className="flex-1 overflow-y-auto">
            <CostDashboard sessionId={activeSessionId} />
          </div>
        )}

        {view === 'dashboard' && !activeSessionId && (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            Select a session to view cost data.
          </div>
        )}

        {view === 'agents' && (
          <div className="flex-1 overflow-y-auto">
            <AgentConfigPanel />
          </div>
        )}

        {view === 'workflows' && (
          <div className="flex-1 overflow-hidden">
            <WorkflowBuilder />
          </div>
        )}
      </main>
    </div>
  );
}
