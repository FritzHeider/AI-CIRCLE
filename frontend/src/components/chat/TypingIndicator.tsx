import React from 'react';

interface TypingAgent {
  agent_id: string;
  agent_name: string;
}

interface TypingIndicatorProps {
  agents: TypingAgent[];
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ agents }) => {
  if (agents.length === 0) return null;

  const names = agents.map((a) => a.agent_name);
  const label =
    names.length === 1
      ? `${names[0]} is typing…`
      : names.length === 2
      ? `${names[0]} and ${names[1]} are typing…`
      : `${names[0]} and ${names.length - 1} others are typing…`;

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-xs text-gray-400">
      <span className="flex gap-1">
        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
        <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
      </span>
      <span>{label}</span>
    </div>
  );
};
