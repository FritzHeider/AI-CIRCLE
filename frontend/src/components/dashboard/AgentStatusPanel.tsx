import React from 'react';
import type { Agent } from '../../types';
import { AgentAvatar } from '../chat/AgentAvatar';

interface AgentStatusPanelProps {
  agents: Agent[];
  onlineAgentIds?: Set<string>;
}

export const AgentStatusPanel: React.FC<AgentStatusPanelProps> = ({
  agents,
  onlineAgentIds = new Set(),
}) => {
  return (
    <div className="p-4">
      <h2 className="text-base font-semibold text-gray-800 mb-3">Agents</h2>
      <ul className="space-y-2">
        {agents.map((agent) => {
          const isOnline = onlineAgentIds.has(agent.id);
          return (
            <li key={agent.id} className="flex items-center gap-2">
              <div className="relative">
                <AgentAvatar agent={agent} name={agent.name} size="sm" />
                <span
                  className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${
                    !agent.enabled ? 'bg-gray-300' : isOnline ? 'bg-green-400' : 'bg-gray-300'
                  }`}
                />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-700 truncate">{agent.name}</p>
                <p className="text-xs text-gray-400 truncate">{agent.adapter_type}</p>
              </div>
              {!agent.enabled && (
                <span className="ml-auto text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                  Off
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};
