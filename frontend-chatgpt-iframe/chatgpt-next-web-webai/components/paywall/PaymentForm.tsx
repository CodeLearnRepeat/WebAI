/**
 * PaymentForm Component
 * 
 * Handles the Stripe payment form for subscription creation.
 * Uses Stripe Elements for secure payment processing.
 */

import React, { useState } from 'react';
import {
  useStripe,
  useElements,
  PaymentElement,
  AddressElement,
} from '@stripe/react-stripe-js';
import { subscriptionApi } from '../../lib/subscription-api';

interface PaymentFormProps {
  customerEmail: string;
  customerName?: string;
  tenantId: string;
  priceId: string;
  onSuccess: () => void;
  onError: (error: string) => void;
}

const PaymentForm: React.FC<PaymentFormProps> = ({
  customerEmail,
  customerName,
  tenantId,
  priceId,
  onSuccess,
  onError,
}) => {
  const stripe = useStripe();
  const elements = useElements();
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      onError('Stripe has not loaded yet. Please try again.');
      return;
    }

    setIsProcessing(true);
    setMessage(null);
    onError(''); // Clear any previous errors

    try {
      // Step 1: Create or get customer
      const customer = await subscriptionApi.getOrCreateCustomer(
        customerEmail,
        customerName
      );

      // Step 2: Create subscription
      const subscription = await subscriptionApi.createSubscription({
        customer_id: customer.customer_id,
        tenant_id: tenantId,
      });

      // Step 3: Confirm payment if needed
      const { error: submitError } = await elements.submit();
      if (submitError) {
        throw new Error(submitError.message || 'Payment submission failed');
      }

      // Step 4: Confirm payment with Stripe
      const { error: confirmError } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: window.location.origin + window.location.pathname + window.location.search,
        },
        redirect: 'if_required',
      });

      if (confirmError) {
        throw new Error(confirmError.message || 'Payment confirmation failed');
      }

      // Success!
      setMessage('Payment successful! Welcome to WebAI Premium!');
      setTimeout(() => {
        onSuccess();
      }, 1000);

    } catch (error) {
      console.error('Payment error:', error);
      const errorMessage = error instanceof Error 
        ? error.message 
        : 'An unexpected error occurred during payment processing';
      
      setMessage('Payment failed: ' + errorMessage);
      onError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="payment-form">
      <div className="payment-section">
        <h3>Payment Information</h3>
        
        <div className="payment-element-container">
          <PaymentElement 
            options={{
              layout: 'tabs',
              paymentMethodOrder: ['card', 'apple_pay', 'google_pay'],
            }}
          />
        </div>
      </div>

      <div className="address-section">
        <h3>Billing Address</h3>
        <div className="address-element-container">
          <AddressElement 
            options={{
              mode: 'billing',
              allowedCountries: ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'ES', 'IT', 'NL'],
              blockPoBox: false,
              fields: {
                phone: 'never',
              },
              validation: {
                phone: {
                  required: 'never',
                },
              },
            }}
          />
        </div>
      </div>

      {message && (
        <div className={`message ${message.includes('successful') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      <button 
        type="submit" 
        disabled={!stripe || !elements || isProcessing}
        className="subscribe-button"
      >
        {isProcessing ? (
          <>
            <span className="processing-spinner"></span>
            Processing...
          </>
        ) : (
          <>
            Subscribe for $2/month
          </>
        )}
      </button>

      <div className="payment-security">
        <div className="security-info">
          <span className="security-icon">🔒</span>
          <span>Your payment information is secure and encrypted</span>
        </div>
      </div>

      <style jsx>{`
        .payment-form {
          width: 100%;
        }

        .payment-section,
        .address-section {
          margin-bottom: 1.5rem;
        }

        .payment-section h3,
        .address-section h3 {
          margin: 0 0 1rem 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: #ffffff;
        }

        .payment-element-container,
        .address-element-container {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 1rem;
        }

        .message {
          padding: 0.75rem 1rem;
          border-radius: 6px;
          margin: 1rem 0;
          text-align: center;
          font-weight: 500;
        }

        .message.success {
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          color: #10b981;
        }

        .message.error {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #ef4444;
        }

        .subscribe-button {
          width: 100%;
          padding: 1rem;
          background: #007bff;
          color: #ffffff;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          font-size: 1rem;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          margin: 1.5rem 0 1rem 0;
        }

        .subscribe-button:hover:not(:disabled) {
          background: #0056b3;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
        }

        .subscribe-button:disabled {
          background: rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.5);
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }

        .processing-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top: 2px solid #ffffff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .payment-security {
          text-align: center;
          margin-top: 1rem;
        }

        .security-info {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.6);
        }

        .security-icon {
          font-size: 1rem;
        }

        /* Override Stripe Elements styling for dark theme */
        :global(.StripeElement) {
          background: transparent !important;
        }

        :global(.StripeElement--focus) {
          border-color: #007bff !important;
        }

        :global(.StripeElement--invalid) {
          border-color: #ef4444 !important;
        }

        @media (max-width: 768px) {
          .payment-element-container,
          .address-element-container {
            padding: 0.75rem;
          }

          .subscribe-button {
            padding: 0.875rem;
            font-size: 0.95rem;
          }
        }
      `}</style>
    </form>
  );
};

export default PaymentForm;