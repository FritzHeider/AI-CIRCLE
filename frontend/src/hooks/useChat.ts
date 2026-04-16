// useChat — manages message list, typing indicators, optimistic sends
import { useState, useCallback, useRef, useEffect } from 'react';
import { api } from '../lib/api';
import type { WSMessage, CostInfo, PresenceInfo } from '../types';

interface TypingAgent {
  agent_id: string;
  agent_name: string;
}

interface UseChatOptions {
  sessionId: string;
}

interface UseChatReturn {
  messages: WSMessage[];
  typingAgents: TypingAgent[];
  latestCost: CostInfo | null;
  isLoadingHistory: boolean;
  handleIncomingMessage: (msg: WSMessage) => void;
  addOptimisticMessage: (content: string, senderId: string, senderName: string) => string;
}

export function useChat({ sessionId }: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [typingAgents, setTypingAgents] = useState<TypingAgent[]>([]);
  const [latestCost, setLatestCost] = useState<CostInfo | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const optimisticIds = useRef<Set<string>>(new Set());

  // Load history on mount / session change
  useEffect(() => {
    if (!sessionId) return;
    setIsLoadingHistory(true);
    api.messages
      .list(sessionId, 50)
      .then((msgs) => setMessages(msgs))
      .catch(console.error)
      .finally(() => setIsLoadingHistory(false));
  }, [sessionId]);

  const handleIncomingMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case 'message': {
        // Skip if this is our own optimistic message
        if (optimisticIds.current.has(msg.id)) {
          optimisticIds.current.delete(msg.id);
          return;
        }
        setMessages((prev) => {
          // Replace optimistic placeholder with real message if same id
          const exists = prev.some((m) => m.id === msg.id);
          if (exists) return prev.map((m) => (m.id === msg.id ? msg : m));
          return [...prev, msg];
        });
        break;
      }

      case 'typing': {
        const presence = msg.presence;
        if (!presence) break;
        if (presence.status === 'typing') {
          setTypingAgents((prev) => {
            if (prev.some((a) => a.agent_id === presence.agent_id)) return prev;
            return [...prev, { agent_id: presence.agent_id, agent_name: presence.agent_name }];
          });
        } else {
          setTypingAgents((prev) =>
            prev.filter((a) => a.agent_id !== presence.agent_id),
          );
        }
        break;
      }

      case 'cost_update': {
        if (msg.cost) setLatestCost(msg.cost);
        break;
      }

      case 'system': {
        setMessages((prev) => [...prev, msg]);
        break;
      }

      case 'error': {
        setMessages((prev) => [...prev, msg]);
        break;
      }

      case 'history': {
        const histMsgs = (msg.metadata?.messages as WSMessage[]) ?? [];
        if (histMsgs.length) setMessages(histMsgs);
        setIsLoadingHistory(false);
        break;
      }

      case 'presence': {
        // Could drive an online list if needed — skip for now
        break;
      }

      default:
        break;
    }
  }, []);

  const addOptimisticMessage = useCallback(
    (content: string, senderId: string, senderName: string): string => {
      const id = `opt-${Date.now()}`;
      const msg: WSMessage = {
        id,
        type: 'message',
        session_id: sessionId,
        sender_id: senderId,
        sender_name: senderName,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        mentions: [],
        artifacts: [],
        metadata: {},
      };
      optimisticIds.current.add(id);
      setMessages((prev) => [...prev, msg]);
      return id;
    },
    [sessionId],
  );

  return {
    messages,
    typingAgents,
    latestCost,
    isLoadingHistory,
    handleIncomingMessage,
    addOptimisticMessage,
  };
}
