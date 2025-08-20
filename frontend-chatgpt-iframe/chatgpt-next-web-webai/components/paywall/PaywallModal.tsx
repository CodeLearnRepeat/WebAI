/**
 * PaywallModal Component
 * 
 * A modal component that handles subscription signup using Stripe Elements.
 * Shows when users try to access protected features without an active subscription.
 */

import React, { useState, useEffect } from 'react';
import { Elements } from '@stripe/react-stripe-js';
import { loadStripe, StripeElementsOptions } from '@stripe/stripe-js';
import PaymentForm from './PaymentForm';
import { getStripe, stripeOptions } from '../../lib/stripe';
import { subscriptionApi, SubscriptionConfig } from '../../lib/subscription-api';

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  userEmail?: string;
  userName?: string;
  tenantId?: string;
}

const PaywallModal: React.FC<PaywallModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  userEmail = '',
  userName = '',
  tenantId = 'default',
}) => {
  const [stripe, setStripe] = useState<any>(null);
  const [config, setConfig] = useState<SubscriptionConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState(userEmail);
  const [name, setName] = useState(userName);

  // Load Stripe and configuration
  useEffect(() => {
    if (isOpen) {
      initializeStripe();
    }
  }, [isOpen]);

  const initializeStripe = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load Stripe configuration
      const subscriptionConfig = await subscriptionApi.getSubscriptionConfig();
      setConfig(subscriptionConfig);

      // Initialize Stripe
      const stripeInstance = await getStripe();
      setStripe(stripeInstance);

      if (!stripeInstance) {
        throw new Error('Failed to initialize Stripe');
      }
    } catch (err) {
      console.error('Failed to initialize Stripe:', err);
      setError(err instanceof Error ? err.message : 'Failed to initialize payment system');
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = () => {
    onSuccess();
    onClose();
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value);
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setName(e.target.value);
  };

  if (!isOpen) return null;

  const elementsOptions: StripeElementsOptions = {
    mode: 'subscription',
    amount: config?.monthly_price_amount || 200,
    currency: config?.currency || 'usd',
    appearance: stripeOptions.appearance,
  };

  return (
    <div className="paywall-overlay">
      <div className="paywall-modal">
        <div className="paywall-header">
          <button className="close-button" onClick={onClose}>
            ×
          </button>
          <div className="paywall-icon">💳</div>
          <h2>Unlock Full Access</h2>
          <p className="paywall-subtitle">
            Subscribe to WebAI for $2/month to access all features
          </p>
        </div>

        <div className="paywall-content">
          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Initializing payment system...</p>
            </div>
          ) : error ? (
            <div className="error-state">
              <div className="error-icon">⚠️</div>
              <p className="error-message">{error}</p>
              <button className="retry-button" onClick={initializeStripe}>
                Try Again
              </button>
            </div>
          ) : (
            <>
              <div className="subscription-details">
                <div className="price-display">
                  <span className="currency">$</span>
                  <span className="amount">2</span>
                  <span className="period">/month</span>
                </div>
                
                <div className="features-list">
                  <div className="feature-item">
                    <span className="feature-icon">✅</span>
                    <span>Full access to setup workflow</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✅</span>
                    <span>Unlimited chat conversations</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✅</span>
                    <span>Document processing & RAG</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✅</span>
                    <span>Priority support</span>
                  </div>
                </div>
              </div>

              <div className="user-info-section">
                <div className="input-group">
                  <label htmlFor="email">Email Address</label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={handleEmailChange}
                    placeholder="your@email.com"
                    required
                  />
                </div>
                
                <div className="input-group">
                  <label htmlFor="name">Full Name (Optional)</label>
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={handleNameChange}
                    placeholder="Your Name"
                  />
                </div>
              </div>

              {stripe && config && email && (
                <Elements stripe={stripe} options={elementsOptions}>
                  <PaymentForm
                    customerEmail={email}
                    customerName={name}
                    tenantId={tenantId}
                    priceId={config.price_id}
                    onSuccess={handleSuccess}
                    onError={setError}
                  />
                </Elements>
              )}

              <div className="paywall-footer">
                <p className="terms-text">
                  By subscribing, you agree to our terms of service. 
                  You can cancel anytime from your account settings.
                </p>
                <div className="security-badges">
                  <span className="security-badge">🔒 Secure payment</span>
                  <span className="security-badge">💳 Powered by Stripe</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <style jsx>{`
        .paywall-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          padding: 1rem;
        }

        .paywall-modal {
          background: #1a1a1a;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          max-width: 500px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          position: relative;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
        }

        .paywall-header {
          padding: 2rem 2rem 1rem 2rem;
          text-align: center;
          position: relative;
        }

        .close-button {
          position: absolute;
          top: 1rem;
          right: 1rem;
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

        .paywall-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .paywall-header h2 {
          margin: 0 0 0.5rem 0;
          font-size: 1.75rem;
          font-weight: 700;
          color: #ffffff;
        }

        .paywall-subtitle {
          margin: 0;
          color: rgba(255, 255, 255, 0.7);
          font-size: 1rem;
          line-height: 1.5;
        }

        .paywall-content {
          padding: 0 2rem 2rem 2rem;
        }

        .loading-state,
        .error-state {
          text-align: center;
          padding: 2rem 0;
        }

        .loading-spinner {
          width: 40px;
          height: 40px;
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
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: background-color 0.2s ease;
        }

        .retry-button:hover {
          background: #0056b3;
        }

        .subscription-details {
          margin-bottom: 2rem;
        }

        .price-display {
          text-align: center;
          margin-bottom: 1.5rem;
        }

        .currency {
          font-size: 1.5rem;
          color: rgba(255, 255, 255, 0.8);
          vertical-align: top;
        }

        .amount {
          font-size: 3rem;
          font-weight: 700;
          color: #ffffff;
        }

        .period {
          font-size: 1rem;
          color: rgba(255, 255, 255, 0.7);
          vertical-align: bottom;
        }

        .features-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .feature-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          color: rgba(255, 255, 255, 0.9);
        }

        .feature-icon {
          font-size: 1rem;
          flex-shrink: 0;
        }

        .user-info-section {
          margin-bottom: 1.5rem;
        }

        .input-group {
          margin-bottom: 1rem;
        }

        .input-group label {
          display: block;
          margin-bottom: 0.5rem;
          color: rgba(255, 255, 255, 0.9);
          font-weight: 500;
          font-size: 0.9rem;
        }

        .input-group input {
          width: 100%;
          padding: 0.75rem;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          color: #ffffff;
          font-size: 1rem;
          transition: border-color 0.2s ease;
        }

        .input-group input:focus {
          outline: none;
          border-color: #007bff;
          box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.2);
        }

        .input-group input::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }

        .paywall-footer {
          margin-top: 2rem;
          padding-top: 1.5rem;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .terms-text {
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.6);
          line-height: 1.4;
          margin: 0 0 1rem 0;
          text-align: center;
        }

        .security-badges {
          display: flex;
          justify-content: center;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .security-badge {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.6);
          display: flex;
          align-items: center;
          gap: 0.25rem;
        }

        @media (max-width: 768px) {
          .paywall-modal {
            margin: 0.5rem;
            max-height: 95vh;
          }

          .paywall-header {
            padding: 1.5rem 1.5rem 1rem 1.5rem;
          }

          .paywall-content {
            padding: 0 1.5rem 1.5rem 1.5rem;
          }

          .paywall-header h2 {
            font-size: 1.5rem;
          }

          .amount {
            font-size: 2.5rem;
          }

          .security-badges {
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
          }
        }
      `}</style>
    </div>
  );
};

export default PaywallModal;