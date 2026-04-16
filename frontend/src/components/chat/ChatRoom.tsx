import React, { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { MessageInput } from './MessageInput';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useChat } from '../../hooks/useChat';
import type { Agent } from '../../types';

interface ChatRoomProps {
  sessionId: string;
  currentAgentId: string;
  currentAgentName: string;
  agents: Agent[];
}

const CURRENT_USER_ID = 'fritz-human';
const CURRENT_USER_NAME = 'Fritz';

export const ChatRoom: React.FC<ChatRoomProps> = ({
  sessionId,
  currentAgentId,
  currentAgentName,
  agents,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    typingAgents,
    latestCost,
    isLoadingHistory,
    handleIncomingMessage,
    addOptimisticMessage,
  } = useChat({ sessionId });

  const { status, sendChat, sendTypingStart, sendTypingStop, isConnected } =
    useWebSocket({
      sessionId,
      agentId: currentAgentId,
      agentName: currentAgentName,
      onMessage: handleIncomingMessage,
    });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typingAgents]);

  const handleSend = (content: string) => {
    addOptimisticMessage(content, currentAgentId, currentAgentName);
    sendChat(content);
  };

  const statusColor = {
    connecting: 'bg-yellow-400',
    connected: 'bg-green-400',
    disconnected: 'bg-red-400',
  }[status];

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span className="text-sm text-gray-600 capitalize">{status}</span>
        </div>
        {latestCost && (
          <div className="text-xs text-gray-500">
            Session: ${latestCost.session_total_usd.toFixed(4)} /{' '}
            ${latestCost.session_budget_usd.toFixed(2)}
            <div className="w-24 h-1 bg-gray-200 rounded-full mt-0.5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  latestCost.budget_pct > 0.8 ? 'bg-red-500' : 'bg-indigo-500'
                }`}
                style={{ width: `${Math.min(latestCost.budget_pct * 100, 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isLoadingHistory ? (
          <div className="flex justify-center py-8 text-gray-400 text-sm">
            Loading history…
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <p className="text-4xl mb-2">💬</p>
            <p className="text-sm">No messages yet. Start the conversation!</p>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isOwn={msg.sender_id === currentAgentId}
            />
          ))
        )}
        <TypingIndicator agents={typingAgents} />
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <MessageInput
        agents={agents}
        onSend={handleSend}
        onTypingStart={sendTypingStart}
        onTypingStop={sendTypingStop}
        disabled={!isConnected}
      />
    </div>
  );
};
