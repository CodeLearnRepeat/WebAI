/**
 * ChatInput Component
 * Simple input field for typing and sending messages
 */

import React, { useState, useRef, useEffect } from 'react';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({ 
  value, 
  onChange, 
  onSend, 
  disabled = false, 
  placeholder = "Type your message..." 
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSend(value);
      }
    }
  };

  const handleSend = () => {
    if (value.trim() && !disabled) {
      onSend(value);
    }
  };

  return (
    <div className="chat-input-container">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="chat-textarea"
        />
        <button 
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="send-button"
          aria-label="Send message"
        >
          <svg viewBox="0 0 24 24" width="20" height="20">
            <path 
              fill="currentColor" 
              d="M2,21L23,12L2,3V10L17,12L2,14V21Z"
            />
          </svg>
        </button>
      </div>

      <style jsx>{`
        .chat-input-container {
          padding: 1rem;
          background: rgba(255, 255, 255, 0.02);
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .input-wrapper {
          display: flex;
          gap: 0.75rem;
          align-items: flex-end;
          max-width: 100%;
        }

        .chat-textarea {
          flex: 1;
          min-height: 44px;
          max-height: 120px;
          padding: 0.75rem;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.05);
          color: #ffffff;
          font-family: inherit;
          font-size: 14px;
          line-height: 1.4;
          resize: none;
          outline: none;
          transition: border-color 0.2s ease;
        }

        .chat-textarea:focus {
          border-color: rgba(255, 255, 255, 0.4);
        }

        .chat-textarea::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }

        .chat-textarea:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .send-button {
          width: 44px;
          height: 44px;
          border: none;
          border-radius: 12px;
          background: #007bff;
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
          flex-shrink: 0;
        }

        .send-button:hover:not(:disabled) {
          background: #0056b3;
          transform: translateY(-1px);
        }

        .send-button:active:not(:disabled) {
          transform: translateY(0);
        }

        .send-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
        }

        @media (max-width: 768px) {
          .chat-input-container {
            padding: 0.75rem;
          }
          
          .input-wrapper {
            gap: 0.5rem;
          }
          
          .send-button {
            width: 40px;
            height: 40px;
          }
        }
      `}</style>
    </div>
  );
}