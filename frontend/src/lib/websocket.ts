// AgentHubWebSocket — WebSocket client with exponential backoff reconnect
import type { WSMessage } from '../types';

type MessageHandler = (msg: WSMessage) => void;
type StatusHandler = (status: 'connecting' | 'connected' | 'disconnected') => void;

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000';

export class AgentHubWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private agentId: string;
  private agentName: string;
  private messageHandlers: Set<MessageHandler> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private retryCount = 0;
  private maxRetries = 8;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private isClosed = false;

  constructor(sessionId: string, agentId: string, agentName: string) {
    this.sessionId = sessionId;
    this.agentId = agentId;
    this.agentName = agentName;
  }

  connect(): void {
    if (this.isClosed) return;
    this._notifyStatus('connecting');

    const url = `${WS_BASE}/ws/${this.sessionId}?agent_id=${encodeURIComponent(this.agentId)}&agent_name=${encodeURIComponent(this.agentName)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.retryCount = 0;
      this._notifyStatus('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WSMessage;
        this.messageHandlers.forEach((h) => h(msg));
      } catch {
        console.warn('AgentHubWS: could not parse message', event.data);
      }
    };

    this.ws.onclose = () => {
      this._notifyStatus('disconnected');
      if (!this.isClosed) this._scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.error('AgentHubWS error:', err);
    };
  }

  disconnect(): void {
    this.isClosed = true;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.ws?.close();
    this.ws = null;
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  sendChat(content: string, replyTo?: string): void {
    this.send({ type: 'chat', content, reply_to: replyTo });
  }

  sendTypingStart(): void {
    this.send({ type: 'typing_start' });
  }

  sendTypingStop(): void {
    this.send({ type: 'typing_stop' });
  }

  sendPing(): void {
    this.send({ type: 'ping' });
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private _notifyStatus(status: 'connecting' | 'connected' | 'disconnected'): void {
    this.statusHandlers.forEach((h) => h(status));
  }

  private _scheduleReconnect(): void {
    if (this.retryCount >= this.maxRetries) {
      console.warn('AgentHubWS: max retries reached');
      return;
    }
    const delay = Math.min(1000 * 2 ** this.retryCount, 30_000);
    this.retryTimer = setTimeout(() => {
      this.retryCount++;
      this.connect();
    }, delay);
  }
}
