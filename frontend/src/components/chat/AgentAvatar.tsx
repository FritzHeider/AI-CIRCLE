import React from 'react';
import type { Agent } from '../../types';

interface AgentAvatarProps {
  agent?: Agent;
  name: string;
  color?: string;
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_CLASSES = {
  sm: 'w-6 h-6 text-xs',
  md: 'w-8 h-8 text-sm',
  lg: 'w-10 h-10 text-base',
};

const ADAPTER_ICONS: Record<string, string> = {
  claude:  '🟣',
  openai:  '🟢',
  gemini:  '🔵',
  falai:   '🟠',
  human:   '👤',
  system:  '⚙️',
};

export const AgentAvatar: React.FC<AgentAvatarProps> = ({
  agent,
  name,
  color,
  size = 'md',
}) => {
  const bgColor = color ?? agent?.avatar_color ?? '#6366f1';
  const adapterType = agent?.adapter_type ?? 'human';
  const icon = ADAPTER_ICONS[adapterType] ?? name.charAt(0).toUpperCase();
  const initials = name.slice(0, 2).toUpperCase();

  return (
    <div
      className={`${SIZE_CLASSES[size]} rounded-full flex items-center justify-center font-medium text-white flex-shrink-0`}
      style={{ backgroundColor: bgColor }}
      title={name}
    >
      {ADAPTER_ICONS[adapterType] ? (
        <span className="leading-none">{icon}</span>
      ) : (
        <span>{initials}</span>
      )}
    </div>
  );
};
