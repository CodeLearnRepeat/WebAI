/**
 * Step 2: Tenant Registration Page
 * Complex form with Basic Setup, RAG Configuration, Advanced Settings tabs
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import WizardLayout, { WizardStep } from '../../components/setup/WizardLayout';
import { WebAITenantSetupApi, TenantRegistrationData, createTenantSetupApi } from '../../lib/webai-api';
import { PaywallProvider, withSubscriptionProtection } from '../../components/paywall/PaywallProvider';

type TabType = 'basic' | 'rag' | 'advanced';

interface FormData {
  tenant_id: string;
  basic_setup: {
    openrouter_api_key: string;
    model_name: string;
    max_tokens: number;
    temperature: number;
    top_p: number;
  };
  rag_config: {
    collection_name: string;
    milvus_host: string;
    milvus_port: number;
    embedding_model: string;
    chunk_size: number;
    chunk_overlap: number;
    enable_hybrid_search: boolean;
  };
  advanced_settings: {
    redis_host: string;
    redis_port: number;
    rate_limit_requests: number;
    rate_limit_window: number;
  };
}

interface ValidationErrors {
  [key: string]: string;
}

const wizardSteps: WizardStep[] = [
  { id: 1, title: 'Welcome', description: 'Introduction to setup', path: '/setup/step1' },
  { id: 2, title: 'Tenant Registration', description: 'Configure your tenant settings', path: '/setup/step2' },
  { id: 3, title: 'System Capabilities', description: 'Review available features', path: '/setup/step3' },
  { id: 4, title: 'File Analysis', description: 'Upload and analyze files', path: '/setup/step4' },
  { id: 5, title: 'File Processing', description: 'Configure processing pipeline', path: '/setup/step5' },
];

function TenantRegistrationPageContent() {
  const router = useRouter();
  const [api, setApi] = useState<WebAITenantSetupApi | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('basic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [apiKeyValidation, setApiKeyValidation] = useState<{ valid: boolean; models?: string[] } | null>(null);
  const [isValidatingKey, setIsValidatingKey] = useState(false);

  const [formData, setFormData] = useState<FormData>({
    tenant_id: '',
    basic_setup: {
      openrouter_api_key: '',
      model_name: 'openai/gpt-4o-mini',
      max_tokens: 2048,
      temperature: 0.7,
      top_p: 0.9,
    },
    rag_config: {
      collection_name: '',
      milvus_host: 'localhost',
      milvus_port: 19530,
      embedding_model: 'voyage-3',
      chunk_size: 1000,
      chunk_overlap: 200,
      enable_hybrid_search: true,
    },
    advanced_settings: {
      redis_host: 'localhost',
      redis_port: 6379,
      rate_limit_requests: 100,
      rate_limit_window: 60,
    },
  });

  useEffect(() => {
    const setupApi = createTenantSetupApi();
    setApi(setupApi);

    // Generate default tenant ID from URL params or timestamp
    const params = new URLSearchParams(window.location.search);
    const defaultTenantId = params.get('tenant') || `tenant-${Date.now()}`;
    
    setFormData(prev => ({
      ...prev,
      tenant_id: defaultTenantId,
      rag_config: {
        ...prev.rag_config,
        collection_name: `${defaultTenantId}_documents`,
      },
    }));
  }, []);

  const validateApiKey = async (apiKey: string) => {
    if (!api || !apiKey.trim()) {
      setApiKeyValidation(null);
      return;
    }

    setIsValidatingKey(true);
    try {
      const result = await api.validateOpenRouterKey(apiKey);
      setApiKeyValidation(result);
      
      if (result.valid && result.models && result.models.length > 0) {
        // Update available models in form
        setFormData(prev => ({
          ...prev,
          basic_setup: {
            ...prev.basic_setup,
            model_name: result.models![0], // Use first available model
          },
        }));
        
        // Clear validation error
        setValidationErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors['basic_setup.openrouter_api_key'];
          return newErrors;
        });
      } else {
        setValidationErrors(prev => ({
          ...prev,
          'basic_setup.openrouter_api_key': 'Invalid API key',
        }));
      }
    } catch (error) {
      console.error('API key validation failed:', error);
      setApiKeyValidation({ valid: false });
      setValidationErrors(prev => ({
        ...prev,
        'basic_setup.openrouter_api_key': 'API key validation failed',
      }));
    } finally {
      setIsValidatingKey(false);
    }
  };

  const handleTenantIdChange = (value: string) => {
    setFormData(prev => ({
      ...prev,
      tenant_id: value,
    }));

    // Clear validation error
    if (validationErrors['tenant_id']) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors['tenant_id'];
        return newErrors;
      });
    }
  };

  const handleNestedInputChange = (section: 'basic_setup' | 'rag_config' | 'advanced_settings', field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));

    // Clear validation error for this field
    const fieldKey = `${section}.${field}`;
    if (validationErrors[fieldKey]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[fieldKey];
        return newErrors;
      });
    }

    // Trigger API key validation
    if (section === 'basic_setup' && field === 'openrouter_api_key') {
      setTimeout(() => validateApiKey(value), 500); // Debounce
    }
  };

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};

    // Basic validation
    if (!formData.tenant_id.trim()) {
      errors['tenant_id'] = 'Tenant ID is required';
    }

    if (!formData.basic_setup.openrouter_api_key.trim()) {
      errors['basic_setup.openrouter_api_key'] = 'OpenRouter API key is required';
    }

    if (!apiKeyValidation?.valid) {
      errors['basic_setup.openrouter_api_key'] = 'Valid API key is required';
    }

    if (!formData.rag_config.collection_name.trim()) {
      errors['rag_config.collection_name'] = 'Collection name is required';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm() || !api) return;

    setIsSubmitting(true);
    try {
      const registrationData: TenantRegistrationData = {
        tenant_id: formData.tenant_id,
        basic_setup: formData.basic_setup,
        rag_config: formData.rag_config,
        advanced_settings: formData.advanced_settings,
      };

      const result = await api.registerTenant(registrationData);
      console.log('Tenant registered:', result);

      // Navigate to next step
      router.push('/setup/step3' + window.location.search);
    } catch (error) {
      console.error('Registration failed:', error);
      setValidationErrors({
        general: error instanceof Error ? error.message : 'Registration failed',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNext = () => {
    handleSubmit();
  };

  const handlePrevious = () => {
    router.push('/setup/step1' + window.location.search);
  };

  const isFormValid = () => {
    return formData.tenant_id.trim() && 
           formData.basic_setup.openrouter_api_key.trim() && 
           apiKeyValidation?.valid &&
           formData.rag_config.collection_name.trim() &&
           Object.keys(validationErrors).length === 0;
  };

  return (
    <>
      <Head>
        <title>Tenant Registration - WebAI Setup</title>
      </Head>

      <WizardLayout
        currentStep={2}
        steps={wizardSteps}
        onNext={handleNext}
        onPrevious={handlePrevious}
        nextDisabled={!isFormValid() || isSubmitting}
        nextLabel={isSubmitting ? 'Creating...' : 'Create Tenant'}
      >
        <div className="registration-form">
          {validationErrors.general && (
            <div className="error-banner">
              {validationErrors.general}
            </div>
          )}

          {/* Tab Navigation */}
          <div className="tab-navigation">
            <button
              onClick={() => setActiveTab('basic')}
              className={`tab-button ${activeTab === 'basic' ? 'active' : ''}`}
            >
              Basic Setup
            </button>
            <button
              onClick={() => setActiveTab('rag')}
              className={`tab-button ${activeTab === 'rag' ? 'active' : ''}`}
            >
              RAG Configuration
            </button>
            <button
              onClick={() => setActiveTab('advanced')}
              className={`tab-button ${activeTab === 'advanced' ? 'active' : ''}`}
            >
              Advanced Settings
            </button>
          </div>

          {/* Tab Content */}
          <div className="tab-content">
            {activeTab === 'basic' && (
              <div className="form-section">
                <h3>Basic Setup</h3>
                <p>Configure your tenant identity and API access.</p>

                <div className="form-group">
                  <label htmlFor="tenant_id">Tenant ID</label>
                  <input
                    id="tenant_id"
                    type="text"
                    value={formData.tenant_id}
                    onChange={(e) => handleTenantIdChange(e.target.value)}
                    className={validationErrors['tenant_id'] ? 'error' : ''}
                    placeholder="Enter unique tenant identifier"
                  />
                  {validationErrors['tenant_id'] && (
                    <span className="error-message">{validationErrors['tenant_id']}</span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="openrouter_api_key">OpenRouter API Key</label>
                  <div className="input-with-validation">
                    <input
                      id="openrouter_api_key"
                      type="password"
                      value={formData.basic_setup.openrouter_api_key}
                      onChange={(e) => handleNestedInputChange('basic_setup', 'openrouter_api_key', e.target.value)}
                      className={validationErrors['basic_setup.openrouter_api_key'] ? 'error' : ''}
                      placeholder="sk-or-..."
                    />
                    {isValidatingKey && (
                      <div className="validation-spinner">
                        <svg className="spinner" viewBox="0 0 24 24">
                          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" strokeDasharray="31.416" strokeDashoffset="31.416">
                            <animate attributeName="stroke-dasharray" dur="2s" values="0 31.416;15.708 15.708;0 31.416" repeatCount="indefinite"/>
                            <animate attributeName="stroke-dashoffset" dur="2s" values="0;-15.708;-31.416" repeatCount="indefinite"/>
                          </circle>
                        </svg>
                      </div>
                    )}
                    {apiKeyValidation && (
                      <div className={`validation-indicator ${apiKeyValidation.valid ? 'valid' : 'invalid'}`}>
                        {apiKeyValidation.valid ? '✓' : '✗'}
                      </div>
                    )}
                  </div>
                  {validationErrors['basic_setup.openrouter_api_key'] && (
                    <span className="error-message">{validationErrors['basic_setup.openrouter_api_key']}</span>
                  )}
                  {apiKeyValidation?.valid && apiKeyValidation.models && (
                    <div className="success-message">
                      ✓ API key validated. {apiKeyValidation.models.length} models available.
                    </div>
                  )}
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="model_name">Model</label>
                    <select
                      id="model_name"
                      value={formData.basic_setup.model_name}
                      onChange={(e) => handleNestedInputChange('basic_setup', 'model_name', e.target.value)}
                    >
                      {apiKeyValidation?.models ? (
                        apiKeyValidation.models.map(model => (
                          <option key={model} value={model}>{model}</option>
                        ))
                      ) : (
                        <option value="openai/gpt-4o-mini">openai/gpt-4o-mini</option>
                      )}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="max_tokens">Max Tokens</label>
                    <input
                      id="max_tokens"
                      type="number"
                      value={formData.basic_setup.max_tokens}
                      onChange={(e) => handleNestedInputChange('basic_setup', 'max_tokens', parseInt(e.target.value))}
                      min="1"
                      max="8192"
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="temperature">Temperature</label>
                    <input
                      id="temperature"
                      type="number"
                      value={formData.basic_setup.temperature}
                      onChange={(e) => handleNestedInputChange('basic_setup', 'temperature', parseFloat(e.target.value))}
                      min="0"
                      max="2"
                      step="0.1"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="top_p">Top P</label>
                    <input
                      id="top_p"
                      type="number"
                      value={formData.basic_setup.top_p}
                      onChange={(e) => handleNestedInputChange('basic_setup', 'top_p', parseFloat(e.target.value))}
                      min="0"
                      max="1"
                      step="0.1"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'rag' && (
              <div className="form-section">
                <h3>RAG Configuration</h3>
                <p>Configure your vector database and retrieval settings.</p>

                <div className="form-group">
                  <label htmlFor="collection_name">Collection Name</label>
                  <input
                    id="collection_name"
                    type="text"
                    value={formData.rag_config.collection_name}
                    onChange={(e) => handleNestedInputChange('rag_config', 'collection_name', e.target.value)}
                    className={validationErrors['rag_config.collection_name'] ? 'error' : ''}
                    placeholder="Documents collection name"
                  />
                  {validationErrors['rag_config.collection_name'] && (
                    <span className="error-message">{validationErrors['rag_config.collection_name']}</span>
                  )}
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="milvus_host">Milvus Host</label>
                    <input
                      id="milvus_host"
                      type="text"
                      value={formData.rag_config.milvus_host}
                      onChange={(e) => handleNestedInputChange('rag_config', 'milvus_host', e.target.value)}
                      placeholder="localhost"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="milvus_port">Milvus Port</label>
                    <input
                      id="milvus_port"
                      type="number"
                      value={formData.rag_config.milvus_port}
                      onChange={(e) => handleNestedInputChange('rag_config', 'milvus_port', parseInt(e.target.value))}
                      min="1"
                      max="65535"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="embedding_model">Embedding Model</label>
                  <select
                    id="embedding_model"
                    value={formData.rag_config.embedding_model}
                    onChange={(e) => handleNestedInputChange('rag_config', 'embedding_model', e.target.value)}
                  >
                    <option value="voyage-3">Voyage AI - voyage-3</option>
                    <option value="voyage-large-2">Voyage AI - voyage-large-2</option>
                    <option value="voyage-code-2">Voyage AI - voyage-code-2</option>
                    <option value="text-embedding-3-small">OpenAI - text-embedding-3-small</option>
                    <option value="text-embedding-3-large">OpenAI - text-embedding-3-large</option>
                  </select>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="chunk_size">Chunk Size</label>
                    <input
                      id="chunk_size"
                      type="number"
                      value={formData.rag_config.chunk_size}
                      onChange={(e) => handleNestedInputChange('rag_config', 'chunk_size', parseInt(e.target.value))}
                      min="100"
                      max="4000"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="chunk_overlap">Chunk Overlap</label>
                    <input
                      id="chunk_overlap"
                      type="number"
                      value={formData.rag_config.chunk_overlap}
                      onChange={(e) => handleNestedInputChange('rag_config', 'chunk_overlap', parseInt(e.target.value))}
                      min="0"
                      max="1000"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.rag_config.enable_hybrid_search}
                      onChange={(e) => handleNestedInputChange('rag_config', 'enable_hybrid_search', e.target.checked)}
                    />
                    <span>Enable Hybrid Search</span>
                    <small>Combines semantic and keyword search for better results</small>
                  </label>
                </div>
              </div>
            )}

            {activeTab === 'advanced' && (
              <div className="form-section">
                <h3>Advanced Settings</h3>
                <p>Configure Redis connection and rate limiting.</p>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="redis_host">Redis Host</label>
                    <input
                      id="redis_host"
                      type="text"
                      value={formData.advanced_settings.redis_host}
                      onChange={(e) => handleNestedInputChange('advanced_settings', 'redis_host', e.target.value)}
                      placeholder="localhost"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="redis_port">Redis Port</label>
                    <input
                      id="redis_port"
                      type="number"
                      value={formData.advanced_settings.redis_port}
                      onChange={(e) => handleNestedInputChange('advanced_settings', 'redis_port', parseInt(e.target.value))}
                      min="1"
                      max="65535"
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="rate_limit_requests">Rate Limit Requests</label>
                    <input
                      id="rate_limit_requests"
                      type="number"
                      value={formData.advanced_settings.rate_limit_requests}
                      onChange={(e) => handleNestedInputChange('advanced_settings', 'rate_limit_requests', parseInt(e.target.value))}
                      min="1"
                      max="10000"
                    />
                    <small>Maximum requests per time window</small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="rate_limit_window">Rate Limit Window (seconds)</label>
                    <input
                      id="rate_limit_window"
                      type="number"
                      value={formData.advanced_settings.rate_limit_window}
                      onChange={(e) => handleNestedInputChange('advanced_settings', 'rate_limit_window', parseInt(e.target.value))}
                      min="1"
                      max="3600"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <style jsx>{`
          .registration-form {
            max-width: 800px;
            margin: 0 auto;
          }

          .error-banner {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
          }

          .tab-navigation {
            display: flex;
            gap: 0.25rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          }

          .tab-button {
            padding: 0.75rem 1.5rem;
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.7);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
            font-weight: 500;
          }

          .tab-button:hover {
            color: #ffffff;
            background: rgba(255, 255, 255, 0.05);
          }

          .tab-button.active {
            color: #007bff;
            border-bottom-color: #007bff;
          }

          .tab-content {
            padding: 0;
          }

          .form-section h3 {
            margin: 0 0 0.5rem 0;
            font-size: 1.25rem;
            font-weight: 600;
          }

          .form-section p {
            margin: 0 0 2rem 0;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.5;
          }

          .form-group {
            margin-bottom: 1.5rem;
          }

          .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1.5rem;
          }

          .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #ffffff;
          }

          .form-group input,
          .form-group select {
            width: 100%;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #ffffff;
            font-size: 0.875rem;
            transition: all 0.2s ease;
          }

          .form-group input:focus,
          .form-group select:focus {
            outline: none;
            border-color: #007bff;
            background: rgba(255, 255, 255, 0.1);
          }

          .form-group input.error,
          .form-group select.error {
            border-color: #ef4444;
            background: rgba(239, 68, 68, 0.1);
          }

          .form-group input::placeholder {
            color: rgba(255, 255, 255, 0.5);
          }

          .form-group small {
            display: block;
            margin-top: 0.25rem;
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.6);
          }

          .input-with-validation {
            position: relative;
            display: flex;
            align-items: center;
          }

          .validation-spinner,
          .validation-indicator {
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .spinner {
            width: 16px;
            height: 16px;
            color: #007bff;
          }

          .validation-indicator {
            font-weight: bold;
            font-size: 1rem;
          }

          .validation-indicator.valid {
            color: #10b981;
          }

          .validation-indicator.invalid {
            color: #ef4444;
          }

          .checkbox-label {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            cursor: pointer;
            color: #ffffff;
          }

          .checkbox-label input[type="checkbox"] {
            width: auto;
            margin: 0;
            margin-top: 0.25rem;
          }

          .checkbox-label span {
            font-weight: 500;
          }

          .checkbox-label small {
            display: block;
            margin-top: 0.25rem;
            color: rgba(255, 255, 255, 0.6);
          }

          .error-message {
            display: block;
            margin-top: 0.5rem;
            color: #fca5a5;
            font-size: 0.75rem;
          }

          .success-message {
            margin-top: 0.5rem;
            color: #6ee7b7;
            font-size: 0.75rem;
          }

          @media (max-width: 768px) {
            .form-row {
              grid-template-columns: 1fr;
              gap: 0;
            }

            .tab-navigation {
              flex-direction: column;
              gap: 0;
            }

            .tab-button {
              text-align: left;
              border-bottom: none;
              border-left: 2px solid transparent;
              padding-left: 1rem;
            }

            .tab-button.active {
              border-bottom-color: transparent;
              border-left-color: #007bff;
              background: rgba(0, 123, 255, 0.1);
            }
          }
        `}</style>
      </WizardLayout>
    </>
  );
}

const ProtectedTenantRegistrationPage = withSubscriptionProtection(TenantRegistrationPageContent, {
  showPaywall: true,
  blockedComponent: (
    <div className="subscription-required-page">
      <Head>
        <title>Subscription Required - WebAI Setup</title>
      </Head>
      
      <WizardLayout
        currentStep={2}
        steps={wizardSteps}
        onNext={() => {}}
        onPrevious={() => window.history.back()}
        nextDisabled={true}
        nextLabel="Subscribe Required"
      >
        <div className="subscription-block">
          <div className="block-icon">🔒</div>
          <h2>Subscription Required</h2>
          <p>
            Access to the tenant setup workflow requires an active WebAI subscription.
            Please subscribe to continue with your setup.
          </p>
          <div className="subscription-features">
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>Complete tenant configuration</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>RAG & embedding setup</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>Advanced system settings</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>Full chat functionality</span>
            </div>
          </div>
          <button
            onClick={() => window.location.href = '/'}
            className="return-button"
          >
            Return to Home & Subscribe
          </button>
        </div>

        <style jsx>{`
          .subscription-required-page {
            min-height: 100vh;
          }

          .subscription-block {
            max-width: 500px;
            margin: 0 auto;
            text-align: center;
            padding: 3rem 2rem;
          }

          .block-icon {
            font-size: 4rem;
            margin-bottom: 1.5rem;
            opacity: 0.7;
          }

          .subscription-block h2 {
            margin: 0 0 1rem 0;
            color: #ffffff;
            font-size: 2rem;
            font-weight: 600;
          }

          .subscription-block p {
            color: rgba(255, 255, 255, 0.7);
            margin: 0 0 2rem 0;
            line-height: 1.6;
            font-size: 1.1rem;
          }

          .subscription-features {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin: 2rem 0;
            text-align: left;
          }

          .feature-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: rgba(255, 255, 255, 0.9);
            font-size: 1rem;
          }

          .feature-icon {
            font-size: 1rem;
            flex-shrink: 0;
          }

          .return-button {
            background: #007bff;
            color: #ffffff;
            border: none;
            padding: 1rem 2rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-top: 1rem;
          }

          .return-button:hover {
            background: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
          }

          @media (max-width: 768px) {
            .subscription-block {
              padding: 2rem 1rem;
            }

            .subscription-block h2 {
              font-size: 1.5rem;
            }

            .subscription-block p {
              font-size: 1rem;
            }
          }
        `}</style>
      </WizardLayout>
    </div>
  )
});

export default function TenantRegistrationPage() {
  return (
    <PaywallProvider autoCheckSubscription={true} debugMode={process.env.NODE_ENV === 'development'}>
      <ProtectedTenantRegistrationPage />
    </PaywallProvider>
  );
}