import React from 'react';
import type { WSMessage, ArtifactInfo } from '../../types';
import { AgentAvatar } from './AgentAvatar';

interface MessageBubbleProps {
  message: WSMessage;
  isOwn: boolean;
}

// Syntax-highlighted code block (plain, no external dep)
const CodeBlock: React.FC<{ artifact: ArtifactInfo }> = ({ artifact }) => (
  <div className="mt-2 rounded-md overflow-hidden">
    {artifact.language && (
      <div className="bg-gray-700 text-gray-300 text-xs px-3 py-1 font-mono">
        {artifact.language}
      </div>
    )}
    <pre className="bg-gray-900 text-green-300 text-xs p-3 overflow-x-auto whitespace-pre-wrap break-words font-mono">
      {artifact.content}
    </pre>
  </div>
);

const ImageArtifact: React.FC<{ artifact: ArtifactInfo }> = ({ artifact }) => (
  <div className="mt-2">
    <img
      src={artifact.url}
      alt={artifact.filename ?? 'Generated image'}
      className="rounded-lg max-w-full max-h-96 object-contain border border-gray-200"
    />
  </div>
);

// Highlight @mentions in plain text
function renderContent(text: string): React.ReactNode {
  const parts = text.split(/(@[\w.\-]+)/g);
  return parts.map((part, i) =>
    part.startsWith('@') ? (
      <span key={i} className="text-indigo-500 font-semibold">
        {part}
      </span>
    ) : (
      part
    ),
  );
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isOwn }) => {
  const isSystem = message.role === 'system' || message.type === 'system';
  const isError = message.type === 'error';

  if (isSystem || isError) {
    return (
      <div className="flex justify-center my-2">
        <div
          className={`text-xs px-3 py-1 rounded-full ${
            isError ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-2 mb-4 ${isOwn ? 'flex-row-reverse' : 'flex-row'}`}>
      <AgentAvatar name={message.sender_name} size="sm" />

      <div className={`flex flex-col max-w-[75%] ${isOwn ? 'items-end' : 'items-start'}`}>
        <div className="flex items-center gap-1 mb-1">
          <span className="text-xs text-gray-500 font-medium">{message.sender_name}</span>
          <span className="text-xs text-gray-400">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>

        <div
          className={`rounded-2xl px-4 py-2 text-sm leading-relaxed ${
            isOwn
              ? 'bg-indigo-600 text-white rounded-tr-sm'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
          }`}
        >
          <p className="whitespace-pre-wrap break-words">
            {renderContent(message.content)}
          </p>

          {/* Artifacts */}
          {message.artifacts?.map((artifact, idx) => (
            <div key={idx}>
              {artifact.type === 'code' && <CodeBlock artifact={artifact} />}
              {artifact.type === 'image' && <ImageArtifact artifact={artifact} />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
