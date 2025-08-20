/**
 * SubscriptionManager Component
 * 
 * Allows users to view and manage their existing subscription.
 * Displays subscription status, billing info, and cancellation options.
 */

import React, { useState, useEffect } from 'react';
import { subscriptionApi, SubscriptionData } from '../../lib/subscription-api';
import { formatSubscriptionStatus, getSubscriptionStatusColor, hasActiveSubscription } from '../../lib/stripe';

interface SubscriptionManagerProps {
  customerId?: string;
  onSubscriptionChange?: () => void;
  compact?: boolean;
}

const SubscriptionManager: React.FC<SubscriptionManagerProps> = ({
  customerId,
  onSubscriptionChange,
  compact = false,
}) => {
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  useEffect(() => {
    loadSubscription();
  }, [customerId]);

  const loadSubscription = async () => {
    try {
      setLoading(true);
      setError(null);

      const customerIdToUse = customerId || subscriptionApi.getCachedCustomerId();
      if (!customerIdToUse) {
        setError('No customer ID available');
        return;
      }

      const result = await subscriptionApi.getSubscriptionStatus(customerIdToUse, false);
      setSubscription(result.subscription_data || null);
    } catch (err) {
      console.error('Failed to load subscription:', err);
      setError(err instanceof Error ? err.message : 'Failed to load subscription');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelSubscription = async (immediate: boolean = false) => {
    if (!subscription) return;

    try {
      setCancelling(true);
      setError(null);

      await subscriptionApi.cancelSubscription(subscription.subscription_id, immediate);
      
      // Reload subscription data
      await loadSubscription();
      
      // Notify parent of subscription change
      onSubscriptionChange?.();
      
      setShowCancelConfirm(false);
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      setError(err instanceof Error ? err.message : 'Failed to cancel subscription');
    } finally {
      setCancelling(false);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatAmount = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  };

  if (loading) {
    return (
      <div className="subscription-manager loading">
        <div className="loading-spinner"></div>
        <p>Loading subscription...</p>
        
        <style jsx>{`
          .subscription-manager.loading {
            text-align: center;
            padding: ${compact ? '1rem' : '2rem'};
          }
          
          .loading-spinner {
            width: 32px;
            height: 32px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top: 3px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem auto;
          }
          
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          
          p {
            color: rgba(255, 255, 255, 0.7);
            margin: 0;
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="subscription-manager error">
        <div className="error-icon">⚠️</div>
        <p className="error-message">{error}</p>
        <button onClick={loadSubscription} className="retry-button">
          Try Again
        </button>
        
        <style jsx>{`
          .subscription-manager.error {
            text-align: center;
            padding: ${compact ? '1rem' : '2rem'};
          }
          
          .error-icon {
            font-size: 2rem;
            margin-bottom: 1rem;
          }
          
          .error-message {
            color: #ef4444;
            margin-bottom: 1rem;
          }
          
          .retry-button {
            background: #007bff;
            color: #ffffff;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s ease;
          }
          
          .retry-button:hover {
            background: #0056b3;
          }
        `}</style>
      </div>
    );
  }

  if (!subscription) {
    return (
      <div className="subscription-manager no-subscription">
        <div className="no-subscription-icon">📭</div>
        <h3>No Active Subscription</h3>
        <p>You don't have an active subscription to manage.</p>
        
        <style jsx>{`
          .subscription-manager.no-subscription {
            text-align: center;
            padding: ${compact ? '1rem' : '2rem'};
          }
          
          .no-subscription-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
          }
          
          h3 {
            margin: 0 0 0.5rem 0;
            color: #ffffff;
            font-size: ${compact ? '1.25rem' : '1.5rem'};
          }
          
          p {
            color: rgba(255, 255, 255, 0.7);
            margin: 0;
          }
        `}</style>
      </div>
    );
  }

  const isActive = hasActiveSubscription(subscription.status);
  const statusColor = getSubscriptionStatusColor(subscription.status);

  return (
    <div className="subscription-manager">
      {!compact && (
        <div className="subscription-header">
          <h2>Subscription Management</h2>
          <p>Manage your WebAI subscription and billing</p>
        </div>
      )}

      <div className="subscription-card">
        <div className="subscription-status">
          <div className="status-indicator">
            <div 
              className="status-dot" 
              style={{ backgroundColor: statusColor }}
            ></div>
            <span className="status-text">
              {formatSubscriptionStatus(subscription.status)}
            </span>
          </div>
          
          <div className="subscription-amount">
            {formatAmount(subscription.amount, subscription.currency)}/{subscription.interval}
          </div>
        </div>

        <div className="subscription-details">
          <div className="detail-row">
            <span className="detail-label">Started:</span>
            <span className="detail-value">
              {formatDate(subscription.created)}
            </span>
          </div>
          
          <div className="detail-row">
            <span className="detail-label">Current Period:</span>
            <span className="detail-value">
              {formatDate(subscription.current_period_start)} - {formatDate(subscription.current_period_end)}
            </span>
          </div>
          
          <div className="detail-row">
            <span className="detail-label">Subscription ID:</span>
            <span className="detail-value subscription-id">
              {subscription.subscription_id}
            </span>
          </div>

          {subscription.cancel_at_period_end && (
            <div className="detail-row cancel-notice">
              <span className="detail-label">⚠️ Notice:</span>
              <span className="detail-value">
                Subscription will cancel at the end of current period
              </span>
            </div>
          )}
        </div>

        {isActive && !subscription.cancel_at_period_end && (
          <div className="subscription-actions">
            <button 
              onClick={() => setShowCancelConfirm(true)}
              className="cancel-button"
              disabled={cancelling}
            >
              Cancel Subscription
            </button>
          </div>
        )}
      </div>

      {/* Cancel Confirmation Modal */}
      {showCancelConfirm && (
        <div className="cancel-modal-overlay">
          <div className="cancel-modal">
            <div className="cancel-modal-header">
              <h3>Cancel Subscription</h3>
              <button 
                className="close-button"
                onClick={() => setShowCancelConfirm(false)}
              >
                ×
              </button>
            </div>
            
            <div className="cancel-modal-content">
              <p>
                Are you sure you want to cancel your subscription? 
                You can choose when the cancellation takes effect:
              </p>
              
              <div className="cancel-options">
                <button
                  onClick={() => handleCancelSubscription(false)}
                  disabled={cancelling}
                  className="cancel-option end-period"
                >
                  <div className="option-title">Cancel at Period End</div>
                  <div className="option-description">
                    Keep access until {formatDate(subscription.current_period_end)}
                  </div>
                </button>
                
                <button
                  onClick={() => handleCancelSubscription(true)}
                  disabled={cancelling}
                  className="cancel-option immediate"
                >
                  <div className="option-title">Cancel Immediately</div>
                  <div className="option-description">
                    Lose access right away (no refund for current period)
                  </div>
                </button>
              </div>
              
              {cancelling && (
                <div className="cancelling-status">
                  <div className="loading-spinner"></div>
                  <span>Processing cancellation...</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .subscription-manager {
          max-width: ${compact ? '100%' : '600px'};
          margin: 0 auto;
        }

        .subscription-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .subscription-header h2 {
          margin: 0 0 0.5rem 0;
          color: #ffffff;
          font-size: 1.75rem;
          font-weight: 700;
        }

        .subscription-header p {
          margin: 0;
          color: rgba(255, 255, 255, 0.7);
        }

        .subscription-card {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: ${compact ? '1rem' : '1.5rem'};
        }

        .subscription-status {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .status-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
        }

        .status-text {
          font-weight: 600;
          color: #ffffff;
        }

        .subscription-amount {
          font-size: 1.25rem;
          font-weight: 700;
          color: #ffffff;
        }

        .subscription-details {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin-bottom: 1.5rem;
        }

        .detail-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
        }

        .detail-row.cancel-notice {
          background: rgba(245, 158, 11, 0.1);
          border: 1px solid rgba(245, 158, 11, 0.3);
          border-radius: 6px;
          padding: 0.75rem;
          margin-top: 0.5rem;
        }

        .detail-label {
          font-weight: 500;
          color: rgba(255, 255, 255, 0.7);
          flex-shrink: 0;
        }

        .detail-value {
          color: #ffffff;
          text-align: right;
          word-break: break-word;
        }

        .subscription-id {
          font-family: monospace;
          font-size: 0.85rem;
        }

        .subscription-actions {
          text-align: center;
        }

        .cancel-button {
          background: transparent;
          color: #ef4444;
          border: 1px solid #ef4444;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .cancel-button:hover:not(:disabled) {
          background: rgba(239, 68, 68, 0.1);
        }

        .cancel-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .cancel-modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10000;
          padding: 1rem;
        }

        .cancel-modal {
          background: #1a1a1a;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          max-width: 500px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
        }

        .cancel-modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem 1.5rem 0 1.5rem;
        }

        .cancel-modal-header h3 {
          margin: 0;
          color: #ffffff;
          font-size: 1.25rem;
        }

        .close-button {
          background: none;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          font-size: 1.5rem;
          cursor: pointer;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 6px;
          transition: all 0.2s ease;
        }

        .close-button:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #ffffff;
        }

        .cancel-modal-content {
          padding: 1.5rem;
        }

        .cancel-modal-content p {
          margin: 0 0 1.5rem 0;
          color: rgba(255, 255, 255, 0.8);
          line-height: 1.5;
        }

        .cancel-options {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .cancel-option {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 1rem;
          cursor: pointer;
          transition: all 0.2s ease;
          text-align: left;
        }

        .cancel-option:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.1);
          border-color: rgba(255, 255, 255, 0.2);
        }

        .cancel-option:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .cancel-option.immediate:hover:not(:disabled) {
          border-color: rgba(239, 68, 68, 0.5);
        }

        .option-title {
          font-weight: 600;
          color: #ffffff;
          margin-bottom: 0.25rem;
        }

        .option-description {
          font-size: 0.9rem;
          color: rgba(255, 255, 255, 0.6);
        }

        .cancelling-status {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          margin-top: 1rem;
          padding: 1rem;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 6px;
          color: rgba(255, 255, 255, 0.8);
        }

        .loading-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.1);
          border-top: 2px solid #007bff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
          .subscription-status {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.75rem;
          }

          .detail-row {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.25rem;
          }

          .detail-value {
            text-align: left;
          }

          .cancel-modal {
            margin: 0.5rem;
          }
        }
      `}</style>
    </div>
  );
};

export default SubscriptionManager;