/**
 * WizardLayout Component
 * Layout wrapper for the tenant setup wizard with navigation and progress tracking
 */

import React from 'react';
import { useRouter } from 'next/router';

export interface WizardStep {
  id: number;
  title: string;
  description: string;
  path: string;
  completed?: boolean;
}

interface WizardLayoutProps {
  currentStep: number;
  steps: WizardStep[];
  children: React.ReactNode;
  onNext?: () => void;
  onPrevious?: () => void;
  onCancel?: () => void;
  nextDisabled?: boolean;
  nextLabel?: string;
  showPrevious?: boolean;
  showNext?: boolean;
}

export default function WizardLayout({
  currentStep,
  steps,
  children,
  onNext,
  onPrevious,
  onCancel,
  nextDisabled = false,
  nextLabel = 'Next',
  showPrevious = true,
  showNext = true
}: WizardLayoutProps) {
  const router = useRouter();

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      // Default behavior - redirect to main chat
      router.push('/embedded/chat' + window.location.search);
    }
  };

  const currentStepData = steps.find(step => step.id === currentStep);
  const currentStepIndex = steps.findIndex(step => step.id === currentStep);
  const progress = ((currentStepIndex + 1) / steps.length) * 100;

  return (
    <div className="wizard-layout">
      {/* Header */}
      <div className="wizard-header">
        <div className="header-content">
          <h1 className="wizard-title">Tenant Setup</h1>
          <button
            onClick={handleCancel}
            className="cancel-button"
            title="Cancel setup"
            aria-label="Cancel setup"
          >
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path 
                fill="currentColor" 
                d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"
              />
            </svg>
          </button>
        </div>
        
        {/* Progress Bar */}
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="progress-text">
            Step {currentStep} of {steps.length}
          </div>
        </div>
      </div>

      {/* Step Navigation */}
      <div className="step-navigation">
        {steps.map((step, index) => (
          <div 
            key={step.id}
            className={`step-item ${step.id === currentStep ? 'active' : ''} ${step.completed ? 'completed' : ''}`}
          >
            <div className="step-indicator">
              {step.completed ? (
                <svg viewBox="0 0 24 24" width="16" height="16">
                  <path 
                    fill="currentColor" 
                    d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"
                  />
                </svg>
              ) : (
                <span>{step.id}</span>
              )}
            </div>
            <div className="step-content">
              <div className="step-title">{step.title}</div>
              <div className="step-description">{step.description}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Current Step Header */}
      {currentStepData && (
        <div className="current-step-header">
          <h2>{currentStepData.title}</h2>
          <p>{currentStepData.description}</p>
        </div>
      )}

      {/* Main Content */}
      <div className="wizard-content">
        {children}
      </div>

      {/* Navigation Buttons */}
      <div className="wizard-navigation">
        {showPrevious && currentStep > 1 && (
          <button
            onClick={onPrevious}
            className="nav-button secondary"
          >
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path 
                fill="currentColor" 
                d="M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z"
              />
            </svg>
            Previous
          </button>
        )}
        
        <div className="nav-spacer" />
        
        <button
          onClick={handleCancel}
          className="nav-button cancel"
        >
          Cancel
        </button>
        
        {showNext && (
          <button
            onClick={onNext}
            disabled={nextDisabled}
            className="nav-button primary"
          >
            {nextLabel}
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path 
                fill="currentColor" 
                d="M4,11V13H16L10.5,18.5L11.92,19.92L19.84,12L11.92,4.08L10.5,5.5L16,11H4Z"
              />
            </svg>
          </button>
        )}
      </div>

      <style jsx>{`
        .wizard-layout {
          min-height: 100vh;
          background: #000000;
          color: #ffffff;
          display: flex;
          flex-direction: column;
        }

        .wizard-header {
          background: rgba(255, 255, 255, 0.02);
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          padding: 1.5rem;
        }

        .header-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 1rem;
        }

        .wizard-title {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
        }

        .cancel-button {
          width: 36px;
          height: 36px;
          border: none;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.1);
          color: rgba(255, 255, 255, 0.7);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }

        .cancel-button:hover {
          background: rgba(239, 68, 68, 0.2);
          color: #fca5a5;
        }

        .progress-container {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .progress-bar {
          flex: 1;
          height: 4px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 2px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #007bff, #0056b3);
          transition: width 0.3s ease;
        }

        .progress-text {
          font-size: 0.875rem;
          color: rgba(255, 255, 255, 0.7);
          white-space: nowrap;
        }

        .step-navigation {
          padding: 1.5rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          gap: 2rem;
          overflow-x: auto;
        }

        .step-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          min-width: 200px;
          opacity: 0.5;
          transition: opacity 0.2s ease;
        }

        .step-item.active {
          opacity: 1;
        }

        .step-item.completed {
          opacity: 0.8;
        }

        .step-indicator {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 0.875rem;
          flex-shrink: 0;
        }

        .step-item.active .step-indicator {
          background: #007bff;
          color: #ffffff;
        }

        .step-item.completed .step-indicator {
          background: #10b981;
          color: #ffffff;
        }

        .step-content {
          min-width: 0;
        }

        .step-title {
          font-weight: 600;
          font-size: 0.875rem;
          margin-bottom: 0.25rem;
        }

        .step-description {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
          line-height: 1.3;
        }

        .current-step-header {
          padding: 2rem 1.5rem 1rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .current-step-header h2 {
          font-size: 1.25rem;
          font-weight: 600;
          margin: 0 0 0.5rem 0;
        }

        .current-step-header p {
          color: rgba(255, 255, 255, 0.7);
          margin: 0;
          line-height: 1.5;
        }

        .wizard-content {
          flex: 1;
          padding: 2rem 1.5rem;
          overflow-y: auto;
        }

        .wizard-navigation {
          padding: 1.5rem;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .nav-spacer {
          flex: 1;
        }

        .nav-button {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.5rem;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          font-weight: 600;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .nav-button.primary {
          background: #007bff;
          border-color: #007bff;
          color: #ffffff;
        }

        .nav-button.primary:hover:not(:disabled) {
          background: #0056b3;
          border-color: #0056b3;
          transform: translateY(-1px);
        }

        .nav-button.secondary {
          background: rgba(255, 255, 255, 0.1);
          color: #ffffff;
        }

        .nav-button.secondary:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: translateY(-1px);
        }

        .nav-button.cancel {
          background: transparent;
          color: rgba(255, 255, 255, 0.7);
        }

        .nav-button.cancel:hover {
          background: rgba(239, 68, 68, 0.1);
          border-color: rgba(239, 68, 68, 0.3);
          color: #fca5a5;
        }

        .nav-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none !important;
        }

        @media (max-width: 768px) {
          .wizard-header,
          .wizard-content,
          .wizard-navigation {
            padding: 1rem;
          }

          .step-navigation {
            padding: 1rem;
            gap: 1rem;
          }

          .step-item {
            min-width: 150px;
          }

          .current-step-header {
            padding: 1.5rem 1rem 0.75rem;
          }

          .wizard-navigation {
            flex-wrap: wrap;
            gap: 0.75rem;
          }

          .nav-button {
            flex: 1;
            min-width: 120px;
            justify-content: center;
          }
        }
      `}</style>
    </div>
  );
}