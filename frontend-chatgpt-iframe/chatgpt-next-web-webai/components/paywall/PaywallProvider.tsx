/**
 * PaywallProvider Component
 * 
 * React Context provider for managing subscription state throughout the application.
 * Provides subscription data, customer information, and paywall logic to child components.
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { subscriptionApi, SubscriptionData, CustomerData } from '../../lib/subscription-api';
import { SubscriptionStatus, hasActiveSubscription } from '../../lib/stripe';

interface PaywallContextValue {
  // Subscription state
  subscription: SubscriptionData | null;
  customer: CustomerData | null;
  hasActiveSubscription: boolean;
  subscriptionStatus: SubscriptionStatus | null;
  
  // Loading states
  isLoading: boolean;
  isInitializing: boolean;
  
  // Error state
  error: string | null;
  
  // Actions
  checkSubscription: (customerId?: string) => Promise<boolean>;
  refreshSubscription: () => Promise<void>;
  setCustomerInfo: (email: string, name?: string) => void;
  clearSubscriptionData: () => void;
  
  // UI state
  showPaywall: boolean;
  setShowPaywall: (show: boolean) => void;
}

const PaywallContext = createContext<PaywallContextValue | undefined>(undefined);

interface PaywallProviderProps {
  children: ReactNode;
  autoCheckSubscription?: boolean;
  debugMode?: boolean;
}

export const PaywallProvider: React.FC<PaywallProviderProps> = ({
  children,
  autoCheckSubscription = true,
  debugMode = false,
}) => {
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [customer, setCustomer] = useState<CustomerData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPaywall, setShowPaywall] = useState(false);

  const debugLog = useCallback((...args: any[]) => {
    if (debugMode) {
      console.log('[PaywallProvider]', ...args);
    }
  }, [debugMode]);

  // Load cached data on initialization
  useEffect(() => {
    loadCachedData();
  }, []);

  // Auto-check subscription on initialization
  useEffect(() => {
    if (autoCheckSubscription && isInitializing) {
      const customerId = subscriptionApi.getCachedCustomerId();
      if (customerId) {
        checkSubscription(customerId).finally(() => {
          setIsInitializing(false);
        });
      } else {
        setIsInitializing(false);
      }
    }
  }, [autoCheckSubscription, isInitializing]);

  const loadCachedData = useCallback(() => {
    try {
      // Load cached customer data
      const cachedCustomerId = subscriptionApi.getCachedCustomerId();
      const cachedCustomerEmail = subscriptionApi.getCachedCustomerEmail();
      
      if (cachedCustomerId && cachedCustomerEmail) {
        setCustomer({
          customer_id: cachedCustomerId,
          email: cachedCustomerEmail,
          created: 0, // We don't cache this
        });
      }

      // Load cached subscription status
      const cachedStatus = subscriptionApi.getCachedSubscriptionStatus();
      debugLog('Loaded cached subscription status:', cachedStatus);
      
    } catch (err) {
      debugLog('Failed to load cached data:', err);
    }
  }, [debugLog]);

  const checkSubscription = useCallback(async (customerId?: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);

      const customerIdToUse = customerId || subscriptionApi.getCachedCustomerId();
      if (!customerIdToUse) {
        debugLog('No customer ID available for subscription check');
        return false;
      }

      debugLog('Checking subscription for customer:', customerIdToUse);
      
      const result = await subscriptionApi.getSubscriptionStatus(customerIdToUse);
      
      if (result.has_subscription && result.subscription_data) {
        setSubscription(result.subscription_data);
        debugLog('Subscription found:', result.subscription_data);
        return hasActiveSubscription(result.subscription_data.status);
      } else {
        setSubscription(null);
        debugLog('No subscription found');
        return false;
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to check subscription';
      debugLog('Subscription check error:', errorMessage);
      setError(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [debugLog]);

  const refreshSubscription = useCallback(async (): Promise<void> => {
    const customerId = customer?.customer_id || subscriptionApi.getCachedCustomerId();
    if (customerId) {
      await checkSubscription(customerId);
    }
  }, [customer, checkSubscription]);

  const setCustomerInfo = useCallback((email: string, name?: string) => {
    const customerData: CustomerData = {
      customer_id: '', // Will be set when customer is created
      email,
      name,
      created: Date.now() / 1000,
    };
    
    setCustomer(customerData);
    debugLog('Customer info set:', customerData);
  }, [debugLog]);

  const clearSubscriptionData = useCallback(() => {
    setSubscription(null);
    setCustomer(null);
    setError(null);
    subscriptionApi.clearCache();
    debugLog('Subscription data cleared');
  }, [debugLog]);

  // Derived state
  const hasActiveSubscriptionValue = subscription ? hasActiveSubscription(subscription.status) : false;
  const subscriptionStatus = subscription?.status || null;

  const contextValue: PaywallContextValue = {
    // Subscription state
    subscription,
    customer,
    hasActiveSubscription: hasActiveSubscriptionValue,
    subscriptionStatus,
    
    // Loading states
    isLoading,
    isInitializing,
    
    // Error state
    error,
    
    // Actions
    checkSubscription,
    refreshSubscription,
    setCustomerInfo,
    clearSubscriptionData,
    
    // UI state
    showPaywall,
    setShowPaywall,
  };

  return (
    <PaywallContext.Provider value={contextValue}>
      {children}
    </PaywallContext.Provider>
  );
};

/**
 * Hook to use the paywall context
 */
export const usePaywall = (): PaywallContextValue => {
  const context = useContext(PaywallContext);
  if (context === undefined) {
    throw new Error('usePaywall must be used within a PaywallProvider');
  }
  return context;
};

/**
 * Hook to check if user has access to protected features
 */
export const useSubscriptionAccess = () => {
  const { hasActiveSubscription, isLoading, isInitializing } = usePaywall();
  
  return {
    hasAccess: hasActiveSubscription,
    isLoading: isLoading || isInitializing,
    needsSubscription: !hasActiveSubscription && !isLoading && !isInitializing,
  };
};

/**
 * Higher-order component to protect routes with subscription check
 */
export interface WithSubscriptionProtectionOptions {
  redirectTo?: string;
  showPaywall?: boolean;
  loadingComponent?: ReactNode;
  blockedComponent?: ReactNode;
}

export const withSubscriptionProtection = <P extends object>(
  Component: React.ComponentType<P>,
  options: WithSubscriptionProtectionOptions = {}
) => {
  const ProtectedComponent: React.FC<P> = (props) => {
    const { hasAccess, isLoading, needsSubscription } = useSubscriptionAccess();
    const { setShowPaywall } = usePaywall();

    useEffect(() => {
      if (needsSubscription && options.showPaywall !== false) {
        setShowPaywall(true);
      }
    }, [needsSubscription, setShowPaywall]);

    if (isLoading) {
      return (
        <>
          {options.loadingComponent || (
            <div className="subscription-loading">
              <div className="loading-spinner"></div>
              <p>Checking subscription...</p>
              
              <style jsx>{`
                .subscription-loading {
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  justify-content: center;
                  min-height: 200px;
                  text-align: center;
                }
                
                .loading-spinner {
                  width: 40px;
                  height: 40px;
                  border: 3px solid rgba(255, 255, 255, 0.1);
                  border-top: 3px solid #007bff;
                  border-radius: 50%;
                  animation: spin 1s linear infinite;
                  margin-bottom: 1rem;
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
          )}
        </>
      );
    }

    if (needsSubscription) {
      // Handle redirect
      if (options.redirectTo && typeof window !== 'undefined') {
        window.location.href = options.redirectTo;
        return null;
      }

      // Show blocked component
      return (
        <>
          {options.blockedComponent || (
            <div className="subscription-required">
              <div className="blocked-icon">🔒</div>
              <h2>Subscription Required</h2>
              <p>
                This feature requires an active WebAI subscription. 
                Please subscribe to continue.
              </p>
              <button 
                onClick={() => setShowPaywall(true)}
                className="subscribe-button"
              >
                Subscribe Now ($2/month)
              </button>
              
              <style jsx>{`
                .subscription-required {
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  justify-content: center;
                  min-height: 300px;
                  text-align: center;
                  padding: 2rem;
                }
                
                .blocked-icon {
                  font-size: 4rem;
                  margin-bottom: 1rem;
                  opacity: 0.7;
                }
                
                h2 {
                  margin: 0 0 1rem 0;
                  color: #ffffff;
                  font-size: 1.75rem;
                  font-weight: 600;
                }
                
                p {
                  color: rgba(255, 255, 255, 0.7);
                  margin: 0 0 2rem 0;
                  line-height: 1.5;
                  max-width: 400px;
                }
                
                .subscribe-button {
                  background: #007bff;
                  color: #ffffff;
                  border: none;
                  padding: 1rem 2rem;
                  border-radius: 8px;
                  font-weight: 600;
                  font-size: 1rem;
                  cursor: pointer;
                  transition: all 0.2s ease;
                }
                
                .subscribe-button:hover {
                  background: #0056b3;
                  transform: translateY(-2px);
                  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
                }
              `}</style>
            </div>
          )}
        </>
      );
    }

    return <Component {...props} />;
  };

  ProtectedComponent.displayName = `withSubscriptionProtection(${Component.displayName || Component.name})`;
  return ProtectedComponent;
};

export default PaywallProvider;