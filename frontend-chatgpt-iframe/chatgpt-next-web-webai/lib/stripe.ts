/**
 * Stripe Configuration
 * 
 * This module handles Stripe initialization and provides the Stripe instance
 * for payment processing throughout the application.
 */

import { loadStripe, Stripe } from '@stripe/stripe-js';

// Stripe publishable key from environment variables
const stripePublishableKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;

// Check if we have a valid Stripe key (not placeholder)
const isValidStripeKey = stripePublishableKey &&
  stripePublishableKey !== 'pk_test_...' &&
  stripePublishableKey !== 'pk_test_' &&
  stripePublishableKey.startsWith('pk_') &&
  stripePublishableKey.length > 20; // Real keys are much longer

const isBuildTime = typeof window === 'undefined' && process.env.NODE_ENV !== 'development';

if (!isValidStripeKey) {
  const errorMsg = `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY environment variable is not set or invalid. Current value: ${stripePublishableKey || 'undefined'}. Please add your actual Stripe publishable key to your environment variables.`;
  
  if (isBuildTime) {
    // During build time, warn but don't throw to allow build to complete
    console.warn('⚠️ STRIPE WARNING (build time):', errorMsg);
    console.warn('⚠️ Stripe functionality will be disabled until a valid key is provided.');
  } else {
    // During runtime, warn but don't throw - allow graceful degradation
    console.warn('⚠️ STRIPE WARNING:', errorMsg);
    console.warn('⚠️ Payment functionality will be disabled. Please configure Stripe keys.');
  }
}

// Stripe instance promise (singleton pattern)
let stripePromise: Promise<Stripe | null>;

/**
 * Get or create Stripe instance
 * This ensures we only load Stripe once per session
 */
export const getStripe = (): Promise<Stripe | null> => {
  // If we don't have a valid key, return null instead of trying to load Stripe
  if (!isValidStripeKey) {
    console.warn('⚠️ STRIPE: Cannot initialize Stripe - invalid or missing publishable key');
    return Promise.resolve(null);
  }

  if (!stripePromise) {
    stripePromise = loadStripe(stripePublishableKey!);
  }
  return stripePromise;
};

/**
 * Stripe configuration options
 */
export const stripeOptions = {
  // Appearance configuration for Stripe Elements
  appearance: {
    theme: 'night' as const,
    variables: {
      colorPrimary: '#007bff',
      colorBackground: '#1a1a1a',
      colorText: '#ffffff',
      colorDanger: '#df1b41',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      spacingUnit: '6px',
      borderRadius: '8px',
    },
    rules: {
      '.Tab': {
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        color: 'rgba(255, 255, 255, 0.8)',
      },
      '.Tab:hover': {
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        color: '#ffffff',
      },
      '.Tab--selected': {
        backgroundColor: '#007bff',
        color: '#ffffff',
      },
      '.Input': {
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        color: '#ffffff',
      },
      '.Input:focus': {
        border: '1px solid #007bff',
        boxShadow: '0 0 0 2px rgba(0, 123, 255, 0.2)',
      },
      '.Label': {
        color: 'rgba(255, 255, 255, 0.9)',
        fontWeight: '500',
      },
    },
  },
};

/**
 * Stripe Elements options for payment forms
 */
export const elementsOptions = {
  mode: 'subscription' as const,
  amount: 200, // $2.00 in cents
  currency: 'usd',
  appearance: stripeOptions.appearance,
  setup_future_usage: 'off_session' as const,
};

/**
 * Payment intent creation options
 */
export interface PaymentIntentOptions {
  amount: number;
  currency: string;
  automatic_payment_methods?: {
    enabled: boolean;
  };
  setup_future_usage?: 'on_session' | 'off_session';
}

/**
 * Subscription creation options
 */
export interface SubscriptionOptions {
  customer_id?: string;
  price_id: string;
  payment_method_id?: string;
  trial_period_days?: number;
}

/**
 * Default subscription price ID (should match backend configuration)
 * This should be set as an environment variable in production
 */
export const DEFAULT_PRICE_ID = process.env.NEXT_PUBLIC_STRIPE_PRICE_ID || 'price_1234567890';

/**
 * Subscription states that the frontend needs to handle
 */
export type SubscriptionStatus = 
  | 'active'
  | 'inactive' 
  | 'canceled'
  | 'past_due'
  | 'unpaid'
  | 'trialing'
  | 'incomplete'
  | 'incomplete_expired';

/**
 * Helper function to check if subscription allows access
 */
export const hasActiveSubscription = (status: SubscriptionStatus | null): boolean => {
  return status === 'active' || status === 'trialing';
};

/**
 * Helper function to format subscription status for display
 */
export const formatSubscriptionStatus = (status: SubscriptionStatus | null): string => {
  if (!status) return 'No subscription';
  
  switch (status) {
    case 'active':
      return 'Active';
    case 'trialing':
      return 'Trial Period';
    case 'past_due':
      return 'Payment Past Due';
    case 'canceled':
      return 'Canceled';
    case 'unpaid':
      return 'Unpaid';
    case 'incomplete':
      return 'Incomplete';
    case 'incomplete_expired':
      return 'Expired';
    case 'inactive':
    default:
      return 'Inactive';
  }
};

/**
 * Helper function to get status color for UI
 */
export const getSubscriptionStatusColor = (status: SubscriptionStatus | null): string => {
  if (!status) return '#6b7280'; // gray
  
  switch (status) {
    case 'active':
    case 'trialing':
      return '#10b981'; // green
    case 'past_due':
    case 'unpaid':
      return '#f59e0b'; // yellow
    case 'canceled':
    case 'incomplete_expired':
      return '#ef4444'; // red
    case 'incomplete':
      return '#8b5cf6'; // purple
    case 'inactive':
    default:
      return '#6b7280'; // gray
  }
};

export default getStripe;