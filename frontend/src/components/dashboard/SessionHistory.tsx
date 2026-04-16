import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';
import type { Session, SessionCreate } from '../../types';

interface SessionHistoryProps {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
}

export const SessionHistory: React.FC<SessionHistoryProps> = ({
  activeSessionId,
  onSelectSession,
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState('');

  const loadSessions = () => {
    api.sessions.list().then(setSessions).catch(console.error);
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const session = await api.sessions.create({ name: newName });
      setSessions((prev) => [session, ...prev]);
      onSelectSession(session.id);
      setNewName('');
      setIsCreating(false);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-800">Sessions</h2>
        <button
          onClick={() => setIsCreating(true)}
          className="text-xs text-indigo-600 hover:text-indigo-800"
        >
          + New
        </button>
      </div>

      {isCreating && (
        <div className="mb-3 flex gap-2">
          <input
            autoFocus
            placeholder="Session name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            className="flex-1 text-sm border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <button
            onClick={handleCreate}
            className="text-xs bg-indigo-600 text-white px-2 py-1 rounded-lg"
          >
            Create
          </button>
          <button
            onClick={() => setIsCreating(false)}
            className="text-xs text-gray-400"
          >
            ✕
          </button>
        </div>
      )}

      <ul className="space-y-1">
        {sessions.map((s) => (
          <li key={s.id}>
            <button
              onClick={() => onSelectSession(s.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                s.id === activeSessionId
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <p className="truncate">{s.name}</p>
              <p className="text-xs text-gray-400 truncate">
                {new Date(s.created_at).toLocaleDateString()}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
