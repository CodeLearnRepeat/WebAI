/**
 * Subscription API Service
 * 
 * This module handles all API calls related to subscription management,
 * integrating with the WebAI backend Stripe subscription system.
 */

import { SubscriptionStatus } from './stripe';

// Get API URL from environment or use default
const getApiUrl = (): string => {
  return process.env.NEXT_PUBLIC_WEBAI_API_URL || 'https://web3ai-backend-v34-api-180395924844.us-central1.run.app';
};

/**
 * Customer data interfaces
 */
export interface CustomerData {
  customer_id: string;
  email: string;
  name?: string;
  created: number;
  metadata?: Record<string, any>;
}

export interface CustomerCreateRequest {
  email: string;
  name?: string;
  metadata?: Record<string, any>;
}

export interface CustomerByEmailRequest {
  email: string;
}

export interface CustomerByEmailResponse {
  found: boolean;
  customer_data?: CustomerData;
}

/**
 * Subscription data interfaces
 */
export interface SubscriptionData {
  subscription_id: string;
  customer_id: string;
  tenant_id: string;
  status: SubscriptionStatus;
  current_period_start: number;
  current_period_end: number;
  cancel_at_period_end: boolean;
  created: number;
  price_id: string;
  amount: number;
  currency: string;
  interval: string;
}

export interface SubscriptionCreateRequest {
  customer_id: string;
  tenant_id: string;
}

export interface SubscriptionStatusResponse {
  has_subscription: boolean;
  subscription_data?: SubscriptionData;
}

export interface SubscriptionCancelRequest {
  immediate?: boolean;
}

export interface SubscriptionCancelResponse {
  subscription_id: string;
  status: string;
  cancelled_at?: number;
  message: string;
}

/**
 * Configuration interfaces
 */
export interface SubscriptionConfig {
  monthly_price_amount: number;
  currency: string;
  interval: string;
  stripe_publishable_key: string;
  price_id: string;
}

/**
 * Local storage keys for subscription caching
 */
const STORAGE_KEYS = {
  CUSTOMER_ID: 'webai_customer_id',
  CUSTOMER_EMAIL: 'webai_customer_email',
  SUBSCRIPTION_STATUS: 'webai_subscription_status',
  SUBSCRIPTION_CACHE_TIME: 'webai_subscription_cache_time',
  SUBSCRIPTION_DATA: 'webai_subscription_data',
} as const;

/**
 * Cache duration for subscription status (5 minutes)
 */
const CACHE_DURATION = 5 * 60 * 1000;

/**
 * Subscription API class
 */
export class SubscriptionApi {
  private apiUrl: string;
  private debug: boolean;

  constructor(debug: boolean = false) {
    this.apiUrl = getApiUrl();
    this.debug = debug;
  }

  private debugLog(...args: any[]) {
    if (this.debug) {
      console.log('[Subscription API]', ...args);
    }
  }

  /**
   * Create HTTP headers for API requests
   */
  private getHeaders(): HeadersInit {
    return {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Handle API response errors
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorMessage;
      } catch {
        if (errorText) errorMessage = errorText;
      }

      throw new Error(errorMessage);
    }

    return response.json();
  }

  /**
   * Local storage helpers
   */
  private setLocalStorage(key: string, value: any): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      this.debugLog('Failed to set localStorage:', error);
    }
  }

  private getLocalStorage<T>(key: string): T | null {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch (error) {
      this.debugLog('Failed to get localStorage:', error);
      return null;
    }
  }

  private removeLocalStorage(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      this.debugLog('Failed to remove localStorage:', error);
    }
  }

  /**
   * Check if subscription status is cached and valid
   */
  private isCacheValid(): boolean {
    const cacheTime = this.getLocalStorage<number>(STORAGE_KEYS.SUBSCRIPTION_CACHE_TIME);
    if (!cacheTime) return false;
    
    const now = Date.now();
    return (now - cacheTime) < CACHE_DURATION;
  }

  /**
   * Get cached subscription data
   */
  private getCachedSubscriptionData(): SubscriptionData | null {
    if (!this.isCacheValid()) return null;
    return this.getLocalStorage<SubscriptionData>(STORAGE_KEYS.SUBSCRIPTION_DATA);
  }

  /**
   * Cache subscription data
   */
  private cacheSubscriptionData(data: SubscriptionData | null): void {
    this.setLocalStorage(STORAGE_KEYS.SUBSCRIPTION_DATA, data);
    this.setLocalStorage(STORAGE_KEYS.SUBSCRIPTION_CACHE_TIME, Date.now());
    
    // Also cache the status separately for quick access
    this.setLocalStorage(STORAGE_KEYS.SUBSCRIPTION_STATUS, data?.status || null);
  }

  /**
   * Get customer ID from cache
   */
  getCachedCustomerId(): string | null {
    return this.getLocalStorage<string>(STORAGE_KEYS.CUSTOMER_ID);
  }

  /**
   * Get customer email from cache
   */
  getCachedCustomerEmail(): string | null {
    return this.getLocalStorage<string>(STORAGE_KEYS.CUSTOMER_EMAIL);
  }

  /**
   * Get cached subscription status
   */
  getCachedSubscriptionStatus(): SubscriptionStatus | null {
    if (!this.isCacheValid()) return null;
    return this.getLocalStorage<SubscriptionStatus>(STORAGE_KEYS.SUBSCRIPTION_STATUS);
  }

  /**
   * Clear all subscription cache
   */
  clearCache(): void {
    Object.values(STORAGE_KEYS).forEach(key => {
      this.removeLocalStorage(key);
    });
    this.debugLog('Subscription cache cleared');
  }

  /**
   * Create a new customer
   */
  async createCustomer(request: CustomerCreateRequest): Promise<CustomerData> {
    this.debugLog('Creating customer:', request.email);
    
    const response = await fetch(`${this.apiUrl}/subscriptions/create-customer`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    const customerData = await this.handleResponse<CustomerData>(response);
    
    // Cache customer data
    this.setLocalStorage(STORAGE_KEYS.CUSTOMER_ID, customerData.customer_id);
    this.setLocalStorage(STORAGE_KEYS.CUSTOMER_EMAIL, customerData.email);
    
    this.debugLog('Customer created:', customerData.customer_id);
    return customerData;
  }

  /**
   * Find customer by email
   */
  async findCustomerByEmail(email: string): Promise<CustomerByEmailResponse> {
    this.debugLog('Finding customer by email:', email);
    
    const response = await fetch(`${this.apiUrl}/subscriptions/find-customer-by-email`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ email }),
    });

    const result = await this.handleResponse<CustomerByEmailResponse>(response);
    
    // Cache customer data if found
    if (result.found && result.customer_data) {
      this.setLocalStorage(STORAGE_KEYS.CUSTOMER_ID, result.customer_data.customer_id);
      this.setLocalStorage(STORAGE_KEYS.CUSTOMER_EMAIL, result.customer_data.email);
    }
    
    this.debugLog('Customer search result:', result);
    return result;
  }

  /**
   * Create a subscription
   */
  async createSubscription(request: SubscriptionCreateRequest): Promise<SubscriptionData> {
    this.debugLog('Creating subscription:', request);
    
    const response = await fetch(`${this.apiUrl}/subscriptions/create-subscription`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    const subscriptionData = await this.handleResponse<SubscriptionData>(response);
    
    // Cache subscription data
    this.cacheSubscriptionData(subscriptionData);
    
    this.debugLog('Subscription created:', subscriptionData.subscription_id);
    return subscriptionData;
  }

  /**
   * Get subscription status for a customer
   */
  async getSubscriptionStatus(customerId: string, useCache: boolean = true): Promise<SubscriptionStatusResponse> {
    // Check cache first if requested
    if (useCache) {
      const cachedData = this.getCachedSubscriptionData();
      if (cachedData) {
        this.debugLog('Using cached subscription data');
        return {
          has_subscription: true,
          subscription_data: cachedData,
        };
      }
    }

    this.debugLog('Fetching subscription status for customer:', customerId);
    
    const response = await fetch(`${this.apiUrl}/subscriptions/status/${customerId}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    const result = await this.handleResponse<SubscriptionStatusResponse>(response);
    
    // Cache the result
    this.cacheSubscriptionData(result.subscription_data || null);
    
    this.debugLog('Subscription status:', result);
    return result;
  }

  /**
   * Cancel a subscription
   */
  async cancelSubscription(
    subscriptionId: string, 
    immediate: boolean = false
  ): Promise<SubscriptionCancelResponse> {
    this.debugLog('Cancelling subscription:', subscriptionId, 'immediate:', immediate);
    
    const response = await fetch(`${this.apiUrl}/subscriptions/cancel/${subscriptionId}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ immediate }),
    });

    const result = await this.handleResponse<SubscriptionCancelResponse>(response);
    
    // Clear cache since subscription status has changed
    this.clearCache();
    
    this.debugLog('Subscription cancelled:', result);
    return result;
  }

  /**
   * Get subscription configuration
   */
  async getSubscriptionConfig(): Promise<SubscriptionConfig> {
    this.debugLog('Fetching subscription config');
    
    const response = await fetch(`${this.apiUrl}/subscriptions/config`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    const config = await this.handleResponse<SubscriptionConfig>(response);
    this.debugLog('Subscription config:', config);
    return config;
  }

  /**
   * Check subscription service health
   */
  async checkHealth(): Promise<{ status: string; message: string; stripe_configured: boolean }> {
    this.debugLog('Checking subscription service health');
    
    const response = await fetch(`${this.apiUrl}/subscriptions/health`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    const health = await this.handleResponse<{ status: string; message: string; stripe_configured: boolean }>(response);
    this.debugLog('Subscription health:', health);
    return health;
  }

  /**
   * Check if user has active subscription
   */
  async hasActiveSubscription(customerId?: string): Promise<boolean> {
    try {
      // Try to get customer ID from parameter or cache
      const customerIdToUse = customerId || this.getCachedCustomerId();
      if (!customerIdToUse) {
        this.debugLog('No customer ID available for subscription check');
        return false;
      }

      const status = await this.getSubscriptionStatus(customerIdToUse);
      const isActive = status.has_subscription && 
        status.subscription_data && 
        (status.subscription_data.status === 'active' || status.subscription_data.status === 'trialing');
      
      this.debugLog('Has active subscription:', isActive);
      return isActive;
    } catch (error) {
      this.debugLog('Error checking subscription status:', error);
      return false;
    }
  }

  /**
   * Get or create customer for an email
   */
  async getOrCreateCustomer(email: string, name?: string): Promise<CustomerData> {
    this.debugLog('Getting or creating customer for:', email);
    
    // First try to find existing customer
    const existingCustomer = await this.findCustomerByEmail(email);
    
    if (existingCustomer.found && existingCustomer.customer_data) {
      this.debugLog('Found existing customer');
      return existingCustomer.customer_data;
    }
    
    // Create new customer if not found
    this.debugLog('Creating new customer');
    return await this.createCustomer({ email, name });
  }
}

/**
 * Default subscription API instance
 */
export const subscriptionApi = new SubscriptionApi(
  process.env.NODE_ENV === 'development'
);

export default subscriptionApi;