/**
 * Step 1: Welcome Page
 * Introduction to the tenant setup workflow
 */

import React from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import WizardLayout, { WizardStep } from '../../components/setup/WizardLayout';

const wizardSteps: WizardStep[] = [
  { id: 1, title: 'Welcome', description: 'Introduction to setup', path: '/setup/step1' },
  { id: 2, title: 'Tenant Registration', description: 'Configure your tenant settings', path: '/setup/step2' },
  { id: 3, title: 'System Capabilities', description: 'Review available features', path: '/setup/step3' },
  { id: 4, title: 'File Analysis', description: 'Upload and analyze files', path: '/setup/step4' },
  { id: 5, title: 'File Processing', description: 'Configure processing pipeline', path: '/setup/step5' },
];

export default function WelcomePage() {
  const router = useRouter();

  const handleNext = () => {
    router.push('/setup/step2' + window.location.search);
  };

  const handleCancel = () => {
    router.push('/embedded/chat' + window.location.search);
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
        nextLabel="Start Setup"
      >
        <div className="welcome-page">
          <div className="welcome-hero">
            <div className="hero-icon">🚀</div>
            <h2>Welcome to WebAI Setup</h2>
            <p className="hero-description">
              Set up your intelligent chat assistant with document processing and RAG capabilities
            </p>
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
                <button onClick={handleNext} className="primary-button">
                  Start Setup →
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
            margin-bottom: 3rem;
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
        `}</style>
      </WizardLayout>
    </>
  );
}