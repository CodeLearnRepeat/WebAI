/**
 * ChatHeader Component
 * Header with title, status indicators, and action buttons
 */

import React from 'react';

interface ChatHeaderProps {
  title: string;
  isConnected: boolean;
  ragEnabled?: boolean;
  onClear?: () => void;
  onClose?: () => void;
}

export default function ChatHeader({ 
  title, 
  isConnected, 
  ragEnabled = false, 
  onClear, 
  onClose 
}: ChatHeaderProps) {
  return (
    <div className="chat-header">
      <div className="header-left">
        <h1 className="chat-title">{title}</h1>
        <div className="status-indicators">
          <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            <div className="status-dot"></div>
            <span>{isConnected ? 'Connected' : 'Connecting...'}</span>
          </div>
          {ragEnabled && (
            <div className="rag-indicator">
              <span>🧠 RAG</span>
            </div>
          )}
        </div>
      </div>
      
      <div className="header-actions">
        {onClear && (
          <button 
            onClick={onClear}
            className="header-button"
            title="Clear conversation"
            aria-label="Clear conversation"
          >
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path 
                fill="currentColor" 
                d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"
              />
            </svg>
          </button>
        )}
        
        {onClose && (
          <button 
            onClick={onClose}
            className="header-button close-button"
            title="Close chat"
            aria-label="Close chat"
          >
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path 
                fill="currentColor" 
                d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"
              />
            </svg>
          </button>
        )}
      </div>

      <style jsx>{`
        .chat-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem;
          background: rgba(255, 255, 255, 0.02);
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          min-height: 60px;
        }

        .header-left {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          flex: 1;
        }

        .chat-title {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: #ffffff;
          line-height: 1.2;
        }

        .status-indicators {
          display: flex;
          gap: 0.75rem;
          align-items: center;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.7);
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #fbbf24;
          transition: background-color 0.3s ease;
        }

        .status-indicator.connected .status-dot {
          background: #10b981;
        }

        .status-indicator.disconnected .status-dot {
          background: #ef4444;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        .rag-indicator {
          padding: 0.25rem 0.5rem;
          background: rgba(59, 130, 246, 0.2);
          border: 1px solid rgba(59, 130, 246, 0.3);
          border-radius: 12px;
          font-size: 11px;
          color: #93c5fd;
        }

        .header-actions {
          display: flex;
          gap: 0.5rem;
          align-items: center;
        }

        .header-button {
          width: 36px;
          height: 36px;
          border: none;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.7);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }

        .header-button:hover {
          background: rgba(255, 255, 255, 0.2);
          color: #ffffff;
          transform: translateY(-1px);
        }

        .header-button:active {
          transform: translateY(0);
        }

        .close-button:hover {
          background: rgba(239, 68, 68, 0.2);
          color: #fca5a5;
        }

        @media (max-width: 768px) {
          .chat-header {
            padding: 0.75rem;
          }
          
          .chat-title {
            font-size: 14px;
          }
          
          .status-indicators {
            gap: 0.5rem;
          }
          
          .header-button {
            width: 32px;
            height: 32px;
          }
        }
      `}</style>
    </div>
  );
}