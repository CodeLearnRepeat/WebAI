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
  openrouter_api_key: string;
  system_prompt: string;
  allowed_domains: string[];
  model: string;
  rate_limit_per_minute: number | null;
  rate_limit_per_hour: number | null;
  rag: RagConfig | null;
  // Legacy UI fields for convenience
  domain_input: string; // For adding domains one by one
}

interface RagConfig {
  enabled: boolean;
  self_rag_enabled: boolean;
  provider: 'milvus';
  milvus: RagMilvusConfig | null;
  embedding_provider: 'sentence_transformers' | 'openai' | 'voyageai';
  embedding_model: string;
  provider_keys: Record<string, string>;
  top_k: number;
}

interface RagMilvusConfig {
  uri: string;
  token: string | null;
  db_name: string | null;
  collection: string;
  vector_field: string;
  text_field: string;
  metadata_field: string | null;
  metric_type: 'IP' | 'COSINE' | 'L2';
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
    openrouter_api_key: '',
    system_prompt: 'You are a helpful AI assistant.',
    allowed_domains: [],
    model: 'anthropic/claude-3.5-sonnet',
    rate_limit_per_minute: 100,
    rate_limit_per_hour: 1000,
    domain_input: '',
    rag: {
      enabled: false,
      self_rag_enabled: false,
      provider: 'milvus',
      milvus: {
        uri: 'http://localhost:19530',
        token: null,
        db_name: null,
        collection: '',
        vector_field: 'embedding',
        text_field: 'text',
        metadata_field: 'metadata',
        metric_type: 'IP'
      },
      embedding_provider: 'sentence_transformers',
      embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
      provider_keys: {},
      top_k: 3
    }
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
      rag: prev.rag ? {
        ...prev.rag,
        milvus: prev.rag.milvus ? {
          ...prev.rag.milvus,
          collection: `${defaultTenantId}_documents`,
        } : null
      } : null,
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
          model: result.models![0], // Use first available model
        }));
        
        // Clear validation error
        setValidationErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors['openrouter_api_key'];
          return newErrors;
        });
      } else {
        setValidationErrors(prev => ({
          ...prev,
          'openrouter_api_key': 'Invalid API key',
        }));
      }
    } catch (error) {
      console.error('API key validation failed:', error);
      setApiKeyValidation({ valid: false });
      setValidationErrors(prev => ({
        ...prev,
        'openrouter_api_key': 'API key validation failed',
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

  const handleInputChange = (field: keyof FormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));

    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }

    // Trigger API key validation
    if (field === 'openrouter_api_key') {
      setTimeout(() => validateApiKey(value), 500); // Debounce
    }
  };

  const handleRagChange = (field: keyof RagConfig, value: any) => {
    setFormData(prev => ({
      ...prev,
      rag: prev.rag ? {
        ...prev.rag,
        [field]: value,
      } : null,
    }));
  };

  const handleMilvusChange = (field: keyof RagMilvusConfig, value: any) => {
    setFormData(prev => ({
      ...prev,
      rag: prev.rag ? {
        ...prev.rag,
        milvus: prev.rag.milvus ? {
          ...prev.rag.milvus,
          [field]: value,
        } : null
      } : null,
    }));
  };

  const addDomain = () => {
    if (formData.domain_input.trim() && !formData.allowed_domains.includes(formData.domain_input.trim())) {
      setFormData(prev => ({
        ...prev,
        allowed_domains: [...prev.allowed_domains, prev.domain_input.trim()],
        domain_input: '',
      }));
    }
  };

  const removeDomain = (index: number) => {
    setFormData(prev => ({
      ...prev,
      allowed_domains: prev.allowed_domains.filter((_, i) => i !== index),
    }));
  };

  const validateForm = (): boolean => {
    const errors: ValidationErrors = {};

    // Basic validation
    if (!formData.tenant_id.trim()) {
      errors['tenant_id'] = 'Tenant ID is required';
    }

    if (!formData.openrouter_api_key.trim()) {
      errors['openrouter_api_key'] = 'OpenRouter API key is required';
    }

    if (!apiKeyValidation?.valid) {
      errors['openrouter_api_key'] = 'Valid API key is required';
    }

    if (!formData.system_prompt.trim()) {
      errors['system_prompt'] = 'System prompt is required';
    }

    if (formData.allowed_domains.length === 0) {
      errors['allowed_domains'] = 'At least one allowed domain is required';
    }

    if (formData.rag?.enabled && (!formData.rag.milvus?.collection.trim())) {
      errors['rag_collection'] = 'Collection name is required when RAG is enabled';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm() || !api) return;

    setIsSubmitting(true);
    try {
      const registrationData: TenantRegistrationData = {
        openrouter_api_key: formData.openrouter_api_key,
        system_prompt: formData.system_prompt,
        allowed_domains: formData.allowed_domains,
        model: formData.model,
        rate_limit_per_minute: formData.rate_limit_per_minute,
        rate_limit_per_hour: formData.rate_limit_per_hour,
        rag: formData.rag,
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
           formData.openrouter_api_key.trim() &&
           formData.system_prompt.trim() &&
           formData.allowed_domains.length > 0 &&
           apiKeyValidation?.valid &&
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
                      value={formData.openrouter_api_key}
                      onChange={(e) => handleInputChange('openrouter_api_key', e.target.value)}
                      className={validationErrors['openrouter_api_key'] ? 'error' : ''}
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
                  {validationErrors['openrouter_api_key'] && (
                    <span className="error-message">{validationErrors['openrouter_api_key']}</span>
                  )}
                  {apiKeyValidation?.valid && apiKeyValidation.models && (
                    <div className="success-message">
                      ✓ API key validated. {apiKeyValidation.models.length} models available.
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="system_prompt">System Prompt <span className="required">*</span></label>
                  <textarea
                    id="system_prompt"
                    value={formData.system_prompt}
                    onChange={(e) => handleInputChange('system_prompt', e.target.value)}
                    className={validationErrors['system_prompt'] ? 'error' : ''}
                    placeholder="You are a helpful AI assistant..."
                    rows={4}
                  />
                  {validationErrors['system_prompt'] && (
                    <span className="error-message">{validationErrors['system_prompt']}</span>
                  )}
                  <small>Define how the AI should behave and respond to users</small>
                </div>

                <div className="form-group">
                  <label htmlFor="allowed_domains">Allowed Domains <span className="required">*</span></label>
                  <div className="domain-input-group">
                    <input
                      id="domain_input"
                      type="text"
                      value={formData.domain_input}
                      onChange={(e) => handleInputChange('domain_input', e.target.value)}
                      placeholder="example.com"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addDomain();
                        }
                      }}
                    />
                    <button type="button" onClick={addDomain} className="add-domain-btn">
                      Add Domain
                    </button>
                  </div>
                  {validationErrors['allowed_domains'] && (
                    <span className="error-message">{validationErrors['allowed_domains']}</span>
                  )}
                  <div className="domain-list">
                    {formData.allowed_domains.map((domain, index) => (
                      <div key={index} className="domain-tag">
                        <span>{domain}</span>
                        <button type="button" onClick={() => removeDomain(index)} className="remove-domain-btn">
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                  <small>Domains where this tenant can be embedded (e.g., example.com, *.example.com)</small>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="model">Model</label>
                    <select
                      id="model"
                      value={formData.model}
                      onChange={(e) => handleInputChange('model', e.target.value)}
                    >
                      {apiKeyValidation?.models ? (
                        apiKeyValidation.models.map(model => (
                          <option key={model} value={model}>{model}</option>
                        ))
                      ) : (
                        <option value="anthropic/claude-3.5-sonnet">anthropic/claude-3.5-sonnet</option>
                      )}
                    </select>
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="rate_limit_per_minute">Rate Limit (per minute)</label>
                    <input
                      id="rate_limit_per_minute"
                      type="number"
                      value={formData.rate_limit_per_minute || ''}
                      onChange={(e) => handleInputChange('rate_limit_per_minute', e.target.value ? parseInt(e.target.value) : null)}
                      min="1"
                      max="1000"
                      placeholder="100"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="rate_limit_per_hour">Rate Limit (per hour)</label>
                    <input
                      id="rate_limit_per_hour"
                      type="number"
                      value={formData.rate_limit_per_hour || ''}
                      onChange={(e) => handleInputChange('rate_limit_per_hour', e.target.value ? parseInt(e.target.value) : null)}
                      min="1"
                      max="10000"
                      placeholder="1000"
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
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={formData.rag?.enabled || false}
                      onChange={(e) => handleRagChange('enabled', e.target.checked)}
                    />
                    <span>Enable RAG</span>
                    <small>Enable Retrieval-Augmented Generation for document search</small>
                  </label>
                </div>

                {formData.rag?.enabled && (
                  <>
                    <div className="form-group">
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={formData.rag.self_rag_enabled || false}
                          onChange={(e) => handleRagChange('self_rag_enabled', e.target.checked)}
                        />
                        <span>Enable Self-RAG</span>
                        <small>Advanced RAG with self-reflection capabilities</small>
                      </label>
                    </div>

                    <div className="form-group">
                      <label htmlFor="collection_name">Collection Name</label>
                      <input
                        id="collection_name"
                        type="text"
                        value={formData.rag.milvus?.collection || ''}
                        onChange={(e) => handleMilvusChange('collection', e.target.value)}
                        className={validationErrors['rag_collection'] ? 'error' : ''}
                        placeholder="Documents collection name"
                      />
                      {validationErrors['rag_collection'] && (
                        <span className="error-message">{validationErrors['rag_collection']}</span>
                      )}
                    </div>

                    <div className="form-group">
                      <label htmlFor="milvus_uri">Milvus URI</label>
                      <input
                        id="milvus_uri"
                        type="text"
                        value={formData.rag.milvus?.uri || ''}
                        onChange={(e) => handleMilvusChange('uri', e.target.value)}
                        placeholder="http://localhost:19530"
                      />
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label htmlFor="milvus_token">Milvus Token (optional)</label>
                        <input
                          id="milvus_token"
                          type="password"
                          value={formData.rag.milvus?.token || ''}
                          onChange={(e) => handleMilvusChange('token', e.target.value || null)}
                          placeholder="Authentication token"
                        />
                      </div>

                      <div className="form-group">
                        <label htmlFor="milvus_db_name">Database Name (optional)</label>
                        <input
                          id="milvus_db_name"
                          type="text"
                          value={formData.rag.milvus?.db_name || ''}
                          onChange={(e) => handleMilvusChange('db_name', e.target.value || null)}
                          placeholder="default"
                        />
                      </div>
                    </div>

                    <div className="form-group">
                      <label htmlFor="embedding_provider">Embedding Provider</label>
                      <select
                        id="embedding_provider"
                        value={formData.rag.embedding_provider}
                        onChange={(e) => handleRagChange('embedding_provider', e.target.value as 'sentence_transformers' | 'openai' | 'voyageai')}
                      >
                        <option value="sentence_transformers">Sentence Transformers (Local)</option>
                        <option value="openai">OpenAI</option>
                        <option value="voyageai">Voyage AI</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="embedding_model">Embedding Model</label>
                      <input
                        id="embedding_model"
                        type="text"
                        value={formData.rag.embedding_model}
                        onChange={(e) => handleRagChange('embedding_model', e.target.value)}
                        placeholder="sentence-transformers/all-MiniLM-L6-v2"
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="top_k">Top K Results</label>
                      <input
                        id="top_k"
                        type="number"
                        value={formData.rag.top_k}
                        onChange={(e) => handleRagChange('top_k', parseInt(e.target.value))}
                        min="1"
                        max="20"
                      />
                      <small>Number of relevant documents to retrieve</small>
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label htmlFor="vector_field">Vector Field</label>
                        <input
                          id="vector_field"
                          type="text"
                          value={formData.rag.milvus?.vector_field || ''}
                          onChange={(e) => handleMilvusChange('vector_field', e.target.value)}
                          placeholder="embedding"
                        />
                      </div>

                      <div className="form-group">
                        <label htmlFor="text_field">Text Field</label>
                        <input
                          id="text_field"
                          type="text"
                          value={formData.rag.milvus?.text_field || ''}
                          onChange={(e) => handleMilvusChange('text_field', e.target.value)}
                          placeholder="text"
                        />
                      </div>
                    </div>

                    <div className="form-group">
                      <label htmlFor="metric_type">Metric Type</label>
                      <select
                        id="metric_type"
                        value={formData.rag.milvus?.metric_type || 'IP'}
                        onChange={(e) => handleMilvusChange('metric_type', e.target.value as 'IP' | 'COSINE' | 'L2')}
                      >
                        <option value="IP">Inner Product (IP)</option>
                        <option value="COSINE">Cosine Similarity</option>
                        <option value="L2">Euclidean Distance (L2)</option>
                      </select>
                    </div>
                  </>
                )}
              </div>
            )}

            {activeTab === 'advanced' && (
              <div className="form-section">
                <h3>Advanced Settings</h3>
                <p>Additional configuration options and provider keys.</p>

                {formData.rag?.enabled && formData.rag.embedding_provider !== 'sentence_transformers' && (
                  <div className="form-group">
                    <label htmlFor="provider_api_key">
                      {formData.rag.embedding_provider === 'openai' ? 'OpenAI API Key' : 'Voyage AI API Key'}
                    </label>
                    <input
                      id="provider_api_key"
                      type="password"
                      value={formData.rag.provider_keys[formData.rag.embedding_provider] || ''}
                      onChange={(e) => {
                        const provider = formData.rag!.embedding_provider;
                        setFormData(prev => ({
                          ...prev,
                          rag: prev.rag ? {
                            ...prev.rag,
                            provider_keys: {
                              ...prev.rag.provider_keys,
                              [provider]: e.target.value
                            }
                          } : null
                        }));
                      }}
                      placeholder={`Enter ${formData.rag.embedding_provider} API key`}
                    />
                    <small>Required for {formData.rag.embedding_provider} embedding provider</small>
                  </div>
                )}

                <div className="form-group">
                  <h4>Form Summary</h4>
                  <div className="summary-info">
                    <p><strong>Tenant ID:</strong> {formData.tenant_id || 'Not set'}</p>
                    <p><strong>Model:</strong> {formData.model}</p>
                    <p><strong>Allowed Domains:</strong> {formData.allowed_domains.length} domain(s)</p>
                    <p><strong>RAG Enabled:</strong> {formData.rag?.enabled ? 'Yes' : 'No'}</p>
                    {formData.rag?.enabled && (
                      <p><strong>Collection:</strong> {formData.rag.milvus?.collection || 'Not set'}</p>
                    )}
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
          .form-group select,
          .form-group textarea {
            width: 100%;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #ffffff;
            font-size: 0.875rem;
            transition: all 0.2s ease;
            font-family: inherit;
            resize: vertical;
          }

          .form-group input:focus,
          .form-group select:focus,
          .form-group textarea:focus {
            outline: none;
            border-color: #007bff;
            background: rgba(255, 255, 255, 0.1);
          }

          .form-group input.error,
          .form-group select.error,
          .form-group textarea.error {
            border-color: #ef4444;
            background: rgba(239, 68, 68, 0.1);
          }

          .form-group input::placeholder,
          .form-group textarea::placeholder {
            color: rgba(255, 255, 255, 0.5);
          }

          .required {
            color: #ef4444;
            font-weight: bold;
          }

          .domain-input-group {
            display: flex;
            gap: 0.5rem;
          }

          .domain-input-group input {
            flex: 1;
          }

          .add-domain-btn {
            padding: 0.75rem 1rem;
            background: #007bff;
            border: none;
            border-radius: 6px;
            color: white;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background 0.2s ease;
            white-space: nowrap;
          }

          .add-domain-btn:hover {
            background: #0056b3;
          }

          .domain-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.5rem;
          }

          .domain-tag {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0.75rem;
            background: rgba(0, 123, 255, 0.2);
            border: 1px solid rgba(0, 123, 255, 0.3);
            border-radius: 20px;
            font-size: 0.75rem;
            color: #ffffff;
          }

          .remove-domain-btn {
            background: none;
            border: none;
            color: #ffffff;
            cursor: pointer;
            font-size: 1rem;
            line-height: 1;
            padding: 0;
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.2s ease;
          }

          .remove-domain-btn:hover {
            background: rgba(255, 255, 255, 0.2);
          }

          .summary-info {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 1rem;
          }

          .summary-info p {
            margin: 0.5rem 0;
            color: rgba(255, 255, 255, 0.9);
          }

          .summary-info strong {
            color: #ffffff;
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