/**
 * ErrorMessage Component
 * Displays error messages with retry functionality
 */

import React from 'react';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export default function ErrorMessage({ 
  message, 
  onRetry, 
  onDismiss 
}: ErrorMessageProps) {
  return (
    <div className="error-message">
      <div className="error-content">
        <div className="error-icon">
          <svg viewBox="0 0 24 24" width="20" height="20">
            <path 
              fill="currentColor" 
              d="M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"
            />
          </svg>
        </div>
        <div className="error-text">
          <p>{message}</p>
        </div>
      </div>
      
      <div className="error-actions">
        {onRetry && (
          <button 
            onClick={onRetry}
            className="error-button retry-button"
          >
            Retry
          </button>
        )}
        {onDismiss && (
          <button 
            onClick={onDismiss}
            className="error-button dismiss-button"
          >
            Dismiss
          </button>
        )}
      </div>

      <style jsx>{`
        .error-message {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.2);
          border-radius: 8px;
          padding: 1rem;
          margin: 0.5rem 0;
        }

        .error-content {
          display: flex;
          gap: 0.75rem;
          align-items: flex-start;
          margin-bottom: 0.75rem;
        }

        .error-icon {
          color: #fca5a5;
          flex-shrink: 0;
          margin-top: 0.1rem;
        }

        .error-text {
          flex: 1;
        }

        .error-text p {
          margin: 0;
          color: #fca5a5;
          font-size: 14px;
          line-height: 1.4;
        }

        .error-actions {
          display: flex;
          gap: 0.5rem;
          justify-content: flex-end;
        }

        .error-button {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .retry-button {
          background: #ef4444;
          color: white;
        }

        .retry-button:hover {
          background: #dc2626;
        }

        .dismiss-button {
          background: rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.7);
        }

        .dismiss-button:hover {
          background: rgba(255, 255, 255, 0.2);
          color: white;
        }
      `}</style>
    </div>
  );
}