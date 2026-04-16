import React, { useState, useRef, useCallback, KeyboardEvent } from 'react';
import type { Agent } from '../../types';

interface MessageInputProps {
  agents: Agent[];
  onSend: (content: string) => void;
  onTypingStart?: () => void;
  onTypingStop?: () => void;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  agents,
  onSend,
  onTypingStart,
  onTypingStop,
  disabled = false,
}) => {
  const [value, setValue] = useState('');
  const [suggestions, setSuggestions] = useState<Agent[]>([]);
  const [suggestionIdx, setSuggestionIdx] = useState(0);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionStart, setMentionStart] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const triggerTyping = useCallback(() => {
    onTypingStart?.();
    if (typingTimer.current) clearTimeout(typingTimer.current);
    typingTimer.current = setTimeout(() => {
      onTypingStop?.();
    }, 2000);
  }, [onTypingStart, onTypingStop]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setValue(text);
    triggerTyping();

    // Detect @mention autocomplete
    const cursor = e.target.selectionStart ?? 0;
    const before = text.slice(0, cursor);
    const match = before.match(/@([\w.]*)$/);
    if (match) {
      const query = match[1].toLowerCase();
      setMentionQuery(query);
      setMentionStart(cursor - match[0].length);
      const filtered = agents.filter(
        (a) =>
          a.name.toLowerCase().includes(query) ||
          a.adapter_type.toLowerCase().includes(query),
      );
      setSuggestions(filtered.slice(0, 5));
      setSuggestionIdx(0);
    } else {
      setSuggestions([]);
      setMentionStart(null);
    }
  };

  const acceptSuggestion = (agent: Agent) => {
    if (mentionStart === null) return;
    const before = value.slice(0, mentionStart);
    const after = value.slice(textareaRef.current?.selectionStart ?? value.length);
    setValue(`${before}@${agent.name} ${after}`);
    setSuggestions([]);
    setMentionStart(null);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSuggestionIdx((i) => Math.min(i + 1, suggestions.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSuggestionIdx((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === 'Tab' || e.key === 'Enter') {
        e.preventDefault();
        acceptSuggestion(suggestions[suggestionIdx]);
        return;
      }
      if (e.key === 'Escape') {
        setSuggestions([]);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    setSuggestions([]);
    onTypingStop?.();
    if (typingTimer.current) clearTimeout(typingTimer.current);
  };

  return (
    <div className="relative border-t border-gray-200 bg-white p-3">
      {/* @mention autocomplete */}
      {suggestions.length > 0 && (
        <div className="absolute bottom-full mb-1 left-3 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-48">
          {suggestions.map((agent, i) => (
            <button
              key={agent.id}
              className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-gray-50 ${
                i === suggestionIdx ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700'
              }`}
              onMouseDown={(e) => {
                e.preventDefault();
                acceptSuggestion(agent);
              }}
            >
              <span
                className="w-5 h-5 rounded-full flex items-center justify-center text-xs text-white"
                style={{ backgroundColor: agent.avatar_color }}
              >
                {agent.name[0]}
              </span>
              <span className="font-medium">@{agent.name}</span>
              <span className="text-gray-400 text-xs">{agent.adapter_type}</span>
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder="Type a message… use @AgentName to mention"
          className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50 max-h-32 overflow-y-auto"
          style={{ minHeight: '2.5rem' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors"
        >
          Send
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-1 ml-1">
        Shift+Enter for new line · Tab to complete @mention
      </p>
    </div>
  );
};
