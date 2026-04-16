// useWebSocket — manages a single AgentHubWebSocket instance per session
import { useEffect, useRef, useState, useCallback } from 'react';
import { AgentHubWebSocket } from '../lib/websocket';
import type { WSMessage } from '../types';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

interface UseWebSocketOptions {
  sessionId: string;
  agentId: string;
  agentName: string;
  onMessage?: (msg: WSMessage) => void;
}

interface UseWebSocketReturn {
  status: ConnectionStatus;
  sendChat: (content: string, replyTo?: string) => void;
  sendTypingStart: () => void;
  sendTypingStop: () => void;
  isConnected: boolean;
}

export function useWebSocket({
  sessionId,
  agentId,
  agentName,
  onMessage,
}: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<AgentHubWebSocket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  useEffect(() => {
    const ws = new AgentHubWebSocket(sessionId, agentId, agentName);
    wsRef.current = ws;

    const unsubStatus = ws.onStatus(setStatus);
    const unsubMsg = onMessage ? ws.onMessage(onMessage) : () => {};

    ws.connect();

    return () => {
      unsubStatus();
      unsubMsg();
      ws.disconnect();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, agentId, agentName]);

  // Re-register message handler when it changes
  useEffect(() => {
    if (!wsRef.current || !onMessage) return;
    const unsub = wsRef.current.onMessage(onMessage);
    return unsub;
  }, [onMessage]);

  const sendChat = useCallback((content: string, replyTo?: string) => {
    wsRef.current?.sendChat(content, replyTo);
  }, []);

  const sendTypingStart = useCallback(() => {
    wsRef.current?.sendTypingStart();
  }, []);

  const sendTypingStop = useCallback(() => {
    wsRef.current?.sendTypingStop();
  }, []);

  return {
    status,
    sendChat,
    sendTypingStart,
    sendTypingStop,
    isConnected: status === 'connected',
  };
}
