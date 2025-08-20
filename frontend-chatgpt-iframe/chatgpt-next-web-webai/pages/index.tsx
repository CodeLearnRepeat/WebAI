/**
 * Welcome Page - Now the root landing page
 * Introduction to the tenant setup workflow
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import WizardLayout, { WizardStep } from '../components/setup/WizardLayout';
import { PaywallProvider, usePaywall, useSubscriptionAccess } from '../components/paywall/PaywallProvider';
import PaywallModal from '../components/paywall/PaywallModal';
import SubscriptionManager from '../components/paywall/SubscriptionManager';

const wizardSteps: WizardStep[] = [
  { id: 1, title: 'Welcome', description: 'Introduction to setup', path: '/' },
  { id: 2, title: 'Tenant Registration', description: 'Configure your tenant settings', path: '/setup/step2' },
  { id: 3, title: 'System Capabilities', description: 'Review available features', path: '/setup/step3' },
  { id: 4, title: 'File Analysis', description: 'Upload and analyze files', path: '/setup/step4' },
  { id: 5, title: 'File Processing', description: 'Configure processing pipeline', path: '/setup/step5' },
];

function WelcomePageContent() {
  const router = useRouter();
  const { hasAccess, needsSubscription } = useSubscriptionAccess();
  const {
    showPaywall,
    setShowPaywall,
    customer,
    subscription,
    hasActiveSubscription: hasActiveSub,
    refreshSubscription,
    setCustomerInfo
  } = usePaywall();
  
  const [showSubscriptionManager, setShowSubscriptionManager] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');

  const handleNext = () => {
    if (!hasAccess) {
      setShowPaywall(true);
      return;
    }
    const search = typeof window !== 'undefined' ? window.location.search : '';
    router.push('/setup/step2' + search);
  };

  const handleCancel = () => {
    const search = typeof window !== 'undefined' ? window.location.search : '';
    router.push('/embedded/chat' + search);
  };

  const handleSubscribe = () => {
    if (email) {
      setCustomerInfo(email, name);
    }
    setShowPaywall(true);
  };

  const handleSubscriptionSuccess = () => {
    refreshSubscription();
    setShowPaywall(false);
  };

  const getTenantId = () => {
    if (typeof window === 'undefined') return 'default';
    const params = new URLSearchParams(window.location.search);
    return params.get('tenant') || 'default';
  };

  return (
    <>
      <Head>
        <title>Welcome - WebAI Setup</title>
      </Head>

      <WizardLayout
        currentStep={1}
        steps={wizardSteps}
        onNext={handleNext}
        onCancel={handleCancel}
        showPrevious={false}
        nextLabel={hasAccess ? "Start Setup" : "Subscribe to Continue"}
      >
        <div className="welcome-page">
          <div className="welcome-hero">
            <div className="hero-icon">🚀</div>
            <h2>Welcome to WebAI Setup</h2>
            <p className="hero-description">
              Set up your intelligent chat assistant with document processing and RAG capabilities
            </p>
          </div>

          <div className="embed-info-link">
            <a href="/embed-info" className="embed-link">
              📖 View Embed Instructions
            </a>
          </div>

          <div className="setup-overview">
            <h3>What you'll accomplish:</h3>
            <div className="features-grid">
              <div className="feature-item">
                <div className="feature-icon">⚙️</div>
                <div className="feature-content">
                  <h4>Tenant Configuration</h4>
                  <p>Configure your API keys, model settings, and RAG parameters for optimal performance</p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">🧠</div>
                <div className="feature-content">
                  <h4>System Capabilities</h4>
                  <p>Review available features, processing limits, and supported file formats</p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">📄</div>
                <div className="feature-content">
                  <h4>Document Analysis</h4>
                  <p>Upload and analyze your documents to get personalized processing recommendations</p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">🔄</div>
                <div className="feature-content">
                  <h4>Knowledge Base Setup</h4>
                  <p>Process your documents and build a searchable knowledge base with vector embeddings</p>
                </div>
              </div>
            </div>
          </div>

          <div className="requirements-section">
            <h3>Before you begin:</h3>
            <div className="requirements-list">
              <div className="requirement-item">
                <span className="requirement-icon">🔑</span>
                <div className="requirement-content">
                  <strong>OpenRouter API Key</strong>
                  <p>You'll need a valid OpenRouter API key to access AI models. Get one at <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer">openrouter.ai</a></p>
                </div>
              </div>

              <div className="requirement-item">
                <span className="requirement-icon">📁</span>
                <div className="requirement-content">
                  <strong>Documents (Optional)</strong>
                  <p>Prepare any documents you want to add to your knowledge base. Supports PDF, DOCX, TXT, MD, and more.</p>
                </div>
              </div>

              <div className="requirement-item">
                <span className="requirement-icon">⏱️</span>
                <div className="requirement-content">
                  <strong>Time Required</strong>
                  <p>Setup typically takes 5-10 minutes, plus additional time for document processing if applicable.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Subscription Status Section */}
          {hasActiveSub && (
            <div className="subscription-status-section">
              <div className="subscription-status-card">
                <div className="status-header">
                  <div className="status-indicator active">
                    <div className="status-dot"></div>
                    <span>Active Subscription</span>
                  </div>
                  <button
                    onClick={() => setShowSubscriptionManager(true)}
                    className="manage-button"
                  >
                    Manage
                  </button>
                </div>
                <p>You have full access to all WebAI features</p>
              </div>
            </div>
          )}

          {/* Subscription Required Section */}
          {needsSubscription && (
            <div className="subscription-required-section">
              <div className="subscription-card">
                <div className="subscription-header">
                  <h3>Subscribe to WebAI</h3>
                  <div className="price-tag">
                    <span className="price">$2</span>
                    <span className="period">/month</span>
                  </div>
                </div>
                
                <div className="subscription-benefits">
                  <div className="benefit-item">
                    <span className="benefit-icon">✅</span>
                    <span>Complete setup workflow access</span>
                  </div>
                  <div className="benefit-item">
                    <span className="benefit-icon">✅</span>
                    <span>Unlimited chat conversations</span>
                  </div>
                  <div className="benefit-item">
                    <span className="benefit-icon">✅</span>
                    <span>Document processing & RAG</span>
                  </div>
                  <div className="benefit-item">
                    <span className="benefit-icon">✅</span>
                    <span>Priority support</span>
                  </div>
                </div>

                <div className="subscription-form">
                  <div className="form-row">
                    <input
                      type="email"
                      placeholder="Enter your email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="email-input"
                    />
                    <input
                      type="text"
                      placeholder="Your name (optional)"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="name-input"
                    />
                  </div>
                  <button
                    onClick={handleSubscribe}
                    disabled={!email}
                    className="subscribe-button"
                  >
                    Subscribe Now
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="getting-started">
            <div className="getting-started-content">
              <h3>Ready to get started?</h3>
              <p>
                This setup wizard will guide you through configuring your WebAI tenant with personalized
                settings and document processing capabilities. You can skip document upload if you prefer
                to add files later.
              </p>
              <div className="getting-started-actions">
                <button onClick={handleCancel} className="secondary-button">
                  Skip Setup
                </button>
                <button
                  onClick={handleNext}
                  className={`primary-button ${!hasAccess ? 'subscription-required' : ''}`}
                  disabled={needsSubscription}
                >
                  {hasAccess ? "Start Setup →" : "Subscribe to Continue"}
                </button>
              </div>
            </div>
          </div>
        </div>

        <style jsx>{`
          .welcome-page {
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
          }

          .welcome-hero {
            margin-bottom: 2rem;
          }

          .hero-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
          }

          .welcome-hero h2 {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0 0 1rem 0;
            background: linear-gradient(135deg, #ffffff, #cccccc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }

          .hero-description {
            font-size: 1.25rem;
            color: rgba(255, 255, 255, 0.8);
            margin: 0;
            line-height: 1.6;
          }

          .embed-info-link {
            margin-bottom: 3rem;
          }

          .embed-link {
            display: inline-block;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: rgba(255, 255, 255, 0.9);
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.95rem;
            transition: all 0.3s ease;
          }

          .embed-link:hover {
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.3);
            color: #ffffff;
            transform: translateY(-1px);
          }

          .setup-overview {
            margin-bottom: 3rem;
            text-align: left;
          }

          .setup-overview h3 {
            text-align: center;
            margin: 0 0 2rem 0;
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
          }

          .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
          }

          .feature-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            text-align: left;
          }

          .feature-icon {
            font-size: 2rem;
            flex-shrink: 0;
          }

          .feature-content h4 {
            margin: 0 0 0.5rem 0;
            font-weight: 600;
            color: #ffffff;
          }

          .feature-content p {
            margin: 0;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.5;
            font-size: 0.9rem;
          }

          .requirements-section {
            margin-bottom: 3rem;
            text-align: left;
          }

          .requirements-section h3 {
            text-align: center;
            margin: 0 0 2rem 0;
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
          }

          .requirements-list {
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
          }

          .requirement-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            align-items: flex-start;
            gap: 1rem;
          }

          .requirement-icon {
            font-size: 1.5rem;
            flex-shrink: 0;
            margin-top: 0.25rem;
          }

          .requirement-content strong {
            display: block;
            margin-bottom: 0.5rem;
            color: #ffffff;
            font-weight: 600;
          }

          .requirement-content p {
            margin: 0;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.5;
            font-size: 0.9rem;
          }

          .requirement-content a {
            color: #93c5fd;
            text-decoration: none;
          }

          .requirement-content a:hover {
            text-decoration: underline;
          }

          .getting-started {
            background: rgba(0, 123, 255, 0.1);
            border: 1px solid rgba(0, 123, 255, 0.2);
            border-radius: 12px;
            padding: 2rem;
          }

          .getting-started-content h3 {
            margin: 0 0 1rem 0;
            font-size: 1.5rem;
            font-weight: 600;
            color: #ffffff;
          }

          .getting-started-content p {
            margin: 0 0 2rem 0;
            color: rgba(255, 255, 255, 0.8);
            line-height: 1.6;
          }

          .getting-started-actions {
            display: flex;
            gap: 1rem;
            justify-content: center;
            align-items: center;
          }

          .primary-button,
          .secondary-button {
            padding: 0.875rem 1.75rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
          }

          .primary-button {
            background: #007bff;
            color: #ffffff;
          }

          .primary-button:hover {
            background: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
          }

          .secondary-button {
            background: transparent;
            color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.3);
          }

          .secondary-button:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.5);
          }

          @media (max-width: 768px) {
            .welcome-hero h2 {
              font-size: 2rem;
            }

            .hero-description {
              font-size: 1.1rem;
            }

            .features-grid {
              grid-template-columns: 1fr;
            }

            .feature-item {
              text-align: center;
              flex-direction: column;
            }

            .requirement-item {
              flex-direction: column;
              text-align: center;
            }

            .getting-started-actions {
              flex-direction: column;
              gap: 0.75rem;
            }

            .primary-button,
            .secondary-button {
              width: 100%;
              max-width: 200px;
            }
          }
          .subscription-status-section {
            margin-bottom: 2rem;
          }

          .subscription-status-card {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 12px;
            padding: 1.5rem;
          }

          .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
          }

          .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
          }

          .status-indicator.active .status-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
          }

          .status-indicator span {
            color: #10b981;
            font-weight: 600;
          }

          .manage-button {
            background: transparent;
            color: #10b981;
            border: 1px solid #10b981;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .manage-button:hover {
            background: rgba(16, 185, 129, 0.1);
          }

          .subscription-status-card p {
            margin: 0;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
          }

          .subscription-required-section {
            margin-bottom: 2rem;
          }

          .subscription-card {
            background: rgba(0, 123, 255, 0.1);
            border: 1px solid rgba(0, 123, 255, 0.3);
            border-radius: 12px;
            padding: 1.5rem;
          }

          .subscription-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
          }

          .subscription-header h3 {
            margin: 0;
            color: #ffffff;
            font-size: 1.25rem;
            font-weight: 600;
          }

          .price-tag {
            display: flex;
            align-items: baseline;
            gap: 0.25rem;
          }

          .price {
            font-size: 1.5rem;
            font-weight: 700;
            color: #007bff;
          }

          .period {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.7);
          }

          .subscription-benefits {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
          }

          .benefit-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.9rem;
          }

          .benefit-icon {
            font-size: 0.9rem;
            flex-shrink: 0;
          }

          .subscription-form {
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }

          .form-row {
            display: flex;
            gap: 0.75rem;
          }

          .email-input,
          .name-input {
            flex: 1;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #ffffff;
            font-size: 0.9rem;
          }

          .email-input::placeholder,
          .name-input::placeholder {
            color: rgba(255, 255, 255, 0.5);
          }

          .email-input:focus,
          .name-input:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.2);
          }

          .subscribe-button {
            background: #007bff;
            color: #ffffff;
            border: none;
            padding: 0.875rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
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

          .primary-button.subscription-required {
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.5);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
          }

          .primary-button.subscription-required:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: none;
            box-shadow: none;
          }

          @media (max-width: 768px) {
            .subscription-header {
              flex-direction: column;
              align-items: flex-start;
              gap: 0.75rem;
            }

            .status-header {
              flex-direction: column;
              align-items: flex-start;
              gap: 0.75rem;
            }

            .form-row {
              flex-direction: column;
            }
          }
        `}</style>

        {/* Paywall Modal */}
        <PaywallModal
          isOpen={showPaywall}
          onClose={() => setShowPaywall(false)}
          onSuccess={handleSubscriptionSuccess}
          userEmail={email || customer?.email || ''}
          userName={name || customer?.name || ''}
          tenantId={getTenantId()}
        />

        {/* Subscription Manager Modal */}
        {showSubscriptionManager && (
          <div className="modal-overlay">
            <div className="modal-content">
              <button
                className="modal-close"
                onClick={() => setShowSubscriptionManager(false)}
              >
                ×
              </button>
              <SubscriptionManager
                customerId={customer?.customer_id}
                onSubscriptionChange={refreshSubscription}
              />
            </div>
          </div>
        )}

        <style jsx>{`
          .modal-overlay {
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

          .modal-content {
            background: #1a1a1a;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            max-width: 600px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
          }

          .modal-close {
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
            z-index: 10001;
          }

          .modal-close:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
          }
        `}</style>
      </WizardLayout>
    </>
  );
}

export default function WelcomePage() {
  return (
    <PaywallProvider autoCheckSubscription={true} debugMode={process.env.NODE_ENV === 'development'}>
      <WelcomePageContent />
    </PaywallProvider>
  );
}