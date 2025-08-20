/**
 * Step 3: System Capabilities Overview
 * Display system processing capabilities and limits
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import WizardLayout, { WizardStep } from '../../components/setup/WizardLayout';
import { WebAITenantSetupApi, SystemCapabilities, createTenantSetupApi } from '../../lib/webai-api';
import { PaywallProvider, withSubscriptionProtection } from '../../components/paywall/PaywallProvider';

const wizardSteps: WizardStep[] = [
  { id: 1, title: 'Welcome', description: 'Introduction to setup', path: '/setup/step1', completed: true },
  { id: 2, title: 'Tenant Registration', description: 'Configure your tenant settings', path: '/setup/step2', completed: true },
  { id: 3, title: 'System Capabilities', description: 'Review available features', path: '/setup/step3' },
  { id: 4, title: 'File Analysis', description: 'Upload and analyze files', path: '/setup/step4' },
  { id: 5, title: 'File Processing', description: 'Configure processing pipeline', path: '/setup/step5' },
];

function SystemCapabilitiesPageContent() {
  const router = useRouter();
  const [api, setApi] = useState<WebAITenantSetupApi | null>(null);
  const [capabilities, setCapabilities] = useState<SystemCapabilities | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const setupApi = createTenantSetupApi();
    setApi(setupApi);
    
    if (setupApi) {
      loadCapabilities(setupApi);
    }
  }, []);

  const loadCapabilities = async (api: WebAITenantSetupApi) => {
    try {
      setIsLoading(true);
      setError(null);
      const caps = await api.getSystemCapabilities();
      setCapabilities(caps);
    } catch (err) {
      console.error('Failed to load system capabilities:', err);
      setError(err instanceof Error ? err.message : 'Failed to load system capabilities');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = () => {
    router.push('/setup/step4' + window.location.search);
  };

  const handlePrevious = () => {
    router.push('/setup/step2' + window.location.search);
  };

  const formatFileSize = (sizeInMB: number) => {
    if (sizeInMB >= 1024) {
      return `${(sizeInMB / 1024).toFixed(1)} GB`;
    }
    return `${sizeInMB} MB`;
  };

  return (
    <>
      <Head>
        <title>System Capabilities - WebAI Setup</title>
      </Head>

      <WizardLayout
        currentStep={3}
        steps={wizardSteps}
        onNext={handleNext}
        onPrevious={handlePrevious}
        nextDisabled={false}
        nextLabel="Continue"
      >
        <div className="capabilities-page">
          {isLoading && (
            <div className="loading-state">
              <div className="loading-spinner">
                <svg className="spinner" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" strokeDasharray="31.416" strokeDashoffset="31.416">
                    <animate attributeName="stroke-dasharray" dur="2s" values="0 31.416;15.708 15.708;0 31.416" repeatCount="indefinite"/>
                    <animate attributeName="stroke-dashoffset" dur="2s" values="0;-15.708;-31.416" repeatCount="indefinite"/>
                  </circle>
                </svg>
              </div>
              <p>Loading system capabilities...</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <div className="error-icon">⚠️</div>
              <h3>Failed to Load Capabilities</h3>
              <p>{error}</p>
              <button 
                onClick={() => api && loadCapabilities(api)}
                className="retry-button"
              >
                Retry
              </button>
            </div>
          )}

          {capabilities && !isLoading && !error && (
            <div className="capabilities-content">
              <div className="intro-section">
                <h3>System Capabilities Overview</h3>
                <p>Review the available features and processing limits for your WebAI tenant setup.</p>
              </div>

              {/* Features Section */}
              <div className="section">
                <h4>🚀 Available Features</h4>
                <div className="feature-grid">
                  <div className={`feature-card ${capabilities.features.rag_processing ? 'enabled' : 'disabled'}`}>
                    <div className="feature-icon">🧠</div>
                    <div className="feature-content">
                      <h5>RAG Processing</h5>
                      <p>Retrieval-Augmented Generation with vector search</p>
                      <div className={`status ${capabilities.features.rag_processing ? 'enabled' : 'disabled'}`}>
                        {capabilities.features.rag_processing ? 'Available' : 'Not Available'}
                      </div>
                    </div>
                  </div>

                  <div className={`feature-card ${capabilities.features.streaming_ingestion ? 'enabled' : 'disabled'}`}>
                    <div className="feature-icon">📡</div>
                    <div className="feature-content">
                      <h5>Streaming Ingestion</h5>
                      <p>Real-time file processing with progress updates</p>
                      <div className={`status ${capabilities.features.streaming_ingestion ? 'enabled' : 'disabled'}`}>
                        {capabilities.features.streaming_ingestion ? 'Available' : 'Not Available'}
                      </div>
                    </div>
                  </div>

                  <div className={`feature-card ${capabilities.features.batch_processing ? 'enabled' : 'disabled'}`}>
                    <div className="feature-icon">📦</div>
                    <div className="feature-content">
                      <h5>Batch Processing</h5>
                      <p>Background processing for large document sets</p>
                      <div className={`status ${capabilities.features.batch_processing ? 'enabled' : 'disabled'}`}>
                        {capabilities.features.batch_processing ? 'Available' : 'Not Available'}
                      </div>
                    </div>
                  </div>

                  <div className={`feature-card ${capabilities.features.hybrid_search ? 'enabled' : 'disabled'}`}>
                    <div className="feature-icon">🔍</div>
                    <div className="feature-content">
                      <h5>Hybrid Search</h5>
                      <p>Combined semantic and keyword search capabilities</p>
                      <div className={`status ${capabilities.features.hybrid_search ? 'enabled' : 'disabled'}`}>
                        {capabilities.features.hybrid_search ? 'Available' : 'Not Available'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Limits Section */}
              <div className="section">
                <h4>📊 Processing Limits</h4>
                <div className="limits-grid">
                  <div className="limit-card">
                    <div className="limit-icon">📄</div>
                    <div className="limit-content">
                      <h5>Max File Size</h5>
                      <div className="limit-value">{formatFileSize(capabilities.limits.max_file_size_mb)}</div>
                      <p>Maximum file size for processing</p>
                    </div>
                  </div>

                  <div className="limit-card">
                    <div className="limit-icon">⚡</div>
                    <div className="limit-content">
                      <h5>Concurrent Jobs</h5>
                      <div className="limit-value">{capabilities.limits.max_concurrent_jobs}</div>
                      <p>Maximum simultaneous processing jobs</p>
                    </div>
                  </div>

                  <div className="limit-card">
                    <div className="limit-icon">🔗</div>
                    <div className="limit-content">
                      <h5>Max Chunk Size</h5>
                      <div className="limit-value">{capabilities.limits.max_chunk_size.toLocaleString()}</div>
                      <p>Maximum characters per document chunk</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Supported Formats Section */}
              <div className="section">
                <h4>📁 Supported File Formats</h4>
                <div className="formats-list">
                  {capabilities.limits.supported_formats.map((format, index) => (
                    <div key={index} className="format-tag">
                      {format.toUpperCase()}
                    </div>
                  ))}
                </div>
              </div>

              {/* Resources Section */}
              <div className="section">
                <h4>🛠️ Available Resources</h4>
                
                <div className="resource-section">
                  <h5>Embedding Models</h5>
                  <div className="resource-list">
                    {capabilities.resources.embedding_models.map((model, index) => (
                      <div key={index} className="resource-item">
                        <span className="resource-name">{model}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="resource-section">
                  <h5>Vector Stores</h5>
                  <div className="resource-list">
                    {capabilities.resources.vector_stores.map((store, index) => (
                      <div key={index} className="resource-item">
                        <span className="resource-name">{store}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="resource-section">
                  <h5>Processing Modes</h5>
                  <div className="resource-list">
                    {capabilities.resources.processing_modes.map((mode, index) => (
                      <div key={index} className="resource-item">
                        <span className="resource-name">{mode}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <style jsx>{`
          .capabilities-page {
            max-width: 900px;
            margin: 0 auto;
          }

          .loading-state {
            text-align: center;
            padding: 4rem 2rem;
          }

          .loading-spinner {
            margin: 0 auto 2rem;
            width: 48px;
            height: 48px;
          }

          .spinner {
            width: 100%;
            height: 100%;
            color: #007bff;
          }

          .loading-state p {
            color: rgba(255, 255, 255, 0.7);
            font-size: 1.1rem;
          }

          .error-state {
            text-align: center;
            padding: 4rem 2rem;
          }

          .error-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .error-state h3 {
            margin: 0 0 1rem 0;
            color: #fca5a5;
          }

          .error-state p {
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 2rem;
          }

          .retry-button {
            padding: 0.75rem 1.5rem;
            background: #007bff;
            border: none;
            border-radius: 6px;
            color: #ffffff;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .retry-button:hover {
            background: #0056b3;
            transform: translateY(-1px);
          }

          .capabilities-content {
            padding: 0;
          }

          .intro-section {
            margin-bottom: 3rem;
          }

          .intro-section h3 {
            margin: 0 0 0.5rem 0;
            font-size: 1.5rem;
            font-weight: 600;
          }

          .intro-section p {
            color: rgba(255, 255, 255, 0.7);
            margin: 0;
            line-height: 1.6;
          }

          .section {
            margin-bottom: 3rem;
          }

          .section h4 {
            margin: 0 0 1.5rem 0;
            font-size: 1.25rem;
            font-weight: 600;
            color: #ffffff;
          }

          .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
          }

          .feature-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            transition: all 0.2s ease;
          }

          .feature-card.enabled {
            border-color: rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.05);
          }

          .feature-card.disabled {
            opacity: 0.6;
            border-color: rgba(239, 68, 68, 0.3);
            background: rgba(239, 68, 68, 0.05);
          }

          .feature-icon {
            font-size: 2rem;
            flex-shrink: 0;
          }

          .feature-content h5 {
            margin: 0 0 0.5rem 0;
            font-weight: 600;
            color: #ffffff;
          }

          .feature-content p {
            margin: 0 0 1rem 0;
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.875rem;
            line-height: 1.4;
          }

          .status {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
          }

          .status.enabled {
            background: rgba(16, 185, 129, 0.2);
            color: #6ee7b7;
          }

          .status.disabled {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
          }

          .limits-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
          }

          .limit-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
          }

          .limit-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
          }

          .limit-content h5 {
            margin: 0 0 0.5rem 0;
            font-weight: 600;
            color: #ffffff;
          }

          .limit-value {
            font-size: 2rem;
            font-weight: 700;
            color: #007bff;
            margin-bottom: 0.5rem;
          }

          .limit-content p {
            margin: 0;
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.875rem;
          }

          .formats-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
          }

          .format-tag {
            background: rgba(0, 123, 255, 0.2);
            border: 1px solid rgba(0, 123, 255, 0.3);
            color: #93c5fd;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
          }

          .resource-section {
            margin-bottom: 2rem;
          }

          .resource-section h5 {
            margin: 0 0 1rem 0;
            font-weight: 600;
            color: #ffffff;
            font-size: 1rem;
          }

          .resource-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
          }

          .resource-item {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            padding: 0.5rem 0.75rem;
          }

          .resource-name {
            color: #ffffff;
            font-size: 0.875rem;
            font-weight: 500;
          }

          @media (max-width: 768px) {
            .feature-grid,
            .limits-grid {
              grid-template-columns: 1fr;
            }

            .feature-card {
              flex-direction: column;
              text-align: center;
            }

            .feature-icon {
              align-self: center;
            }

            .formats-list,
            .resource-list {
              justify-content: center;
            }
          }
        `}</style>
      </WizardLayout>
    </>
  );
}

const ProtectedSystemCapabilitiesPage = withSubscriptionProtection(SystemCapabilitiesPageContent, {
  showPaywall: true,
  blockedComponent: (
    <div className="subscription-required-page">
      <Head>
        <title>Subscription Required - WebAI Setup</title>
      </Head>
      
      <WizardLayout
        currentStep={3}
        steps={wizardSteps}
        onNext={() => {}}
        onPrevious={() => window.history.back()}
        nextDisabled={true}
        nextLabel="Subscribe Required"
      >
        <div className="subscription-block">
          <div className="block-icon">🔒</div>
          <h2>Premium Feature Access</h2>
          <p>
            System capabilities overview is available to subscribers only.
            Get insights into processing limits, supported formats, and available features.
          </p>
          <button 
            onClick={() => window.location.href = '/'}
            className="return-button"
          >
            Return to Home & Subscribe
          </button>
        </div>

        <style jsx>{`
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
          }

          .return-button:hover {
            background: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
          }
        `}</style>
      </WizardLayout>
    </div>
  )
});

export default function SystemCapabilitiesPage() {
  return (
    <PaywallProvider autoCheckSubscription={true} debugMode={process.env.NODE_ENV === 'development'}>
      <ProtectedSystemCapabilitiesPage />
    </PaywallProvider>
  );
}