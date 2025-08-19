/**
 * ChatMessages Component
 * Renders the list of chat messages with markdown support
 */

import React from 'react';
import { ChatMessage } from '@/lib/webai-api';

// Simple markdown parser for basic formatting
function parseSimpleMarkdown(text: string): string {
  return text
    // Code blocks
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    // Line breaks
    .replace(/\n/g, '<br>');
}

interface ChatMessagesProps {
  messages: ChatMessage[];
  isLoading?: boolean;
  isStreaming?: boolean;
}

export default function ChatMessages({ messages, isLoading, isStreaming }: ChatMessagesProps) {
  return (
    <div className="chat-messages">
      {messages.map((message, index) => (
        <div key={message.id || index} className={`message message-${message.role}`}>
          <div className="message-avatar">
            {message.role === 'user' ? '👤' : '🤖'}
          </div>
          <div className="message-content">
            {message.role === 'assistant' ? (
              <div
                dangerouslySetInnerHTML={{
                  __html: parseSimpleMarkdown(message.content)
                }}
              />
            ) : (
              <p>{message.content}</p>
            )}
          </div>
        </div>
      ))}
      
      {isLoading && (
        <div className="message message-assistant">
          <div className="message-avatar">🤖</div>
          <div className="message-content">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .chat-messages {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .message {
          display: flex;
          gap: 0.75rem;
          max-width: 100%;
        }

        .message-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          font-size: 14px;
        }

        .message-content {
          flex: 1;
          background: rgba(255, 255, 255, 0.05);
          padding: 0.75rem 1rem;
          border-radius: 1rem;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .message-user .message-content {
          background: rgba(255, 255, 255, 0.1);
          border-color: rgba(255, 255, 255, 0.2);
        }

        .message-content p {
          margin: 0;
          line-height: 1.5;
        }

        .message-content :global(pre) {
          background: rgba(0, 0, 0, 0.3);
          padding: 1rem;
          border-radius: 0.5rem;
          overflow-x: auto;
          margin: 0.5rem 0;
        }

        .message-content :global(code.inline-code) {
          background: rgba(255, 255, 255, 0.1);
          padding: 0.2rem 0.4rem;
          border-radius: 0.25rem;
          font-size: 0.9em;
        }

        .message-content :global(.table-wrapper) {
          overflow-x: auto;
          margin: 0.5rem 0;
        }

        .message-content :global(table) {
          width: 100%;
          border-collapse: collapse;
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .message-content :global(th),
        .message-content :global(td) {
          padding: 0.5rem;
          border: 1px solid rgba(255, 255, 255, 0.1);
          text-align: left;
        }

        .message-content :global(th) {
          background: rgba(255, 255, 255, 0.1);
          font-weight: 600;
        }

        .typing-indicator {
          display: flex;
          gap: 0.25rem;
          align-items: center;
        }

        .typing-indicator span {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.6);
          animation: typing 1.4s infinite ease-in-out;
        }

        .typing-indicator span:nth-child(1) {
          animation-delay: -0.32s;
        }

        .typing-indicator span:nth-child(2) {
          animation-delay: -0.16s;
        }

        @keyframes typing {
          0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}