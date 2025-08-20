/**
 * Step 4: File Analysis Page
 * File upload with drag & drop interface and analysis results
 */

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import WizardLayout, { WizardStep } from '../../components/setup/WizardLayout';
import { WebAITenantSetupApi, FileAnalysisResult, createTenantSetupApi } from '../../lib/webai-api';
import { PaywallProvider, withSubscriptionProtection } from '../../components/paywall/PaywallProvider';

console.log('[DEBUG] step4.tsx loaded - imports verified');

const wizardSteps: WizardStep[] = [
  { id: 1, title: 'Welcome', description: 'Introduction to setup', path: '/setup/step1', completed: true },
  { id: 2, title: 'Tenant Registration', description: 'Configure your tenant settings', path: '/setup/step2', completed: true },
  { id: 3, title: 'System Capabilities', description: 'Review available features', path: '/setup/step3', completed: true },
  { id: 4, title: 'File Analysis', description: 'Upload and analyze files', path: '/setup/step4' },
  { id: 5, title: 'File Processing', description: 'Configure processing pipeline', path: '/setup/step5' },
];

interface UploadedFile {
  file: File;
  analysis?: FileAnalysisResult;
  isAnalyzing?: boolean;
  error?: string;
}

function FileAnalysisPageContent() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [api, setApi] = useState<WebAITenantSetupApi | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    const setupApi = createTenantSetupApi();
    setApi(setupApi);
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files) as File[];
    console.log('[DEBUG] Files dropped:', files.length, 'files');
    handleFiles(files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []) as File[];
    console.log('[DEBUG] Files selected:', files.length, 'files');
    handleFiles(files);
  };

  const handleFiles = (files: File[]) => {
    const validFiles = files.filter(file => validateFile(file));
    
    if (validFiles.length > 0) {
      const newFiles: UploadedFile[] = validFiles.map(file => ({ file }));
      setUploadedFiles(prev => [...prev, ...newFiles]);
      
      // Start analyzing files
      validFiles.forEach((file, index) => {
        const fileIndex = uploadedFiles.length + index;
        console.log(`[DEBUG] Starting analysis for file ${index + 1}/${validFiles.length}: ${file.name} at index ${fileIndex}`);
        analyzeFile(file, fileIndex);
      });
    }
  };

  const validateFile = (file: File): boolean => {
    const maxSize = 100 * 1024 * 1024; // 100MB
    const supportedTypes = [
      'application/pdf',
      'text/plain',
      'text/markdown',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/csv',
      'application/json',
      'text/html',
      'application/rtf'
    ];

    if (file.size > maxSize) {
      alert(`File "${file.name}" is too large. Maximum size is 100MB.`);
      return false;
    }

    if (!supportedTypes.includes(file.type) && !file.name.match(/\.(txt|md|pdf|doc|docx|csv|json|html|rtf)$/i)) {
      alert(`File "${file.name}" is not a supported format.`);
      return false;
    }

    return true;
  };

  const analyzeFile = async (file: File, index: number) => {
    if (!api) {
      console.error('[DEBUG] No API available for file analysis');
      return;
    }

    console.log(`[DEBUG] Analyzing file: ${file.name} (${file.size} bytes) at index ${index}`);

    setUploadedFiles(prev =>
      prev.map((item, i) =>
        i === index ? { ...item, isAnalyzing: true, error: undefined } : item
      )
    );

    setIsAnalyzing(true);

    try {
      const analysis = await api.analyzeFile(file);
      console.log(`[DEBUG] Analysis completed for ${file.name}:`, analysis);
      
      setUploadedFiles(prev =>
        prev.map((item, i) =>
          i === index ? { ...item, analysis, isAnalyzing: false } : item
        )
      );
    } catch (error) {
      console.error(`[DEBUG] File analysis failed for ${file.name}:`, error);
      
      setUploadedFiles(prev =>
        prev.map((item, i) =>
          i === index ? {
            ...item,
            isAnalyzing: false,
            error: error instanceof Error ? error.message : 'Analysis failed'
          } : item
        )
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const retryAnalysis = (index: number) => {
    const file = uploadedFiles[index];
    if (file) {
      analyzeFile(file.file, index);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatProcessingTime = (timeStr: string): string => {
    // Convert time estimates to more readable format
    if (timeStr.includes('seconds')) {
      return timeStr;
    } else if (timeStr.includes('minutes')) {
      return timeStr;
    }
    return timeStr;
  };

  const hasAnalyzedFiles = uploadedFiles.some(file => file.analysis);
  const hasErrors = uploadedFiles.some(file => file.error);

  const handleNext = () => {
    // Store file analysis results in session storage for next step
    const analysisResults = uploadedFiles
      .filter(file => file.analysis)
      .map(file => ({
        filename: file.file.name,
        size: file.file.size,
        type: file.file.type,
        analysis: file.analysis!
      }));
    
    console.log('[DEBUG] Saving analysis results for', analysisResults.length, 'files to session storage');
    sessionStorage.setItem('fileAnalysisResults', JSON.stringify(analysisResults));
    router.push('/setup/step5' + window.location.search);
  };

  const handlePrevious = () => {
    router.push('/setup/step3' + window.location.search);
  };

  return (
    <>
      <Head>
        <title>File Analysis - WebAI Setup</title>
      </Head>

      <WizardLayout
        currentStep={4}
        steps={wizardSteps}
        onNext={handleNext}
        onPrevious={handlePrevious}
        nextDisabled={!hasAnalyzedFiles || isAnalyzing}
        nextLabel="Continue to Processing"
      >
        <div className="file-analysis-page">
          <div className="intro-section">
            <h3>File Analysis</h3>
            <p>Upload your documents to analyze their content and get processing recommendations.</p>
          </div>

          {/* File Upload Area */}
          <div 
            className={`upload-area ${isDragOver ? 'drag-over' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="upload-icon">📁</div>
            <h4>Drop files here or click to browse</h4>
            <p>Supports PDF, TXT, DOCX, MD, CSV, JSON, HTML, RTF files up to 100MB</p>
            
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.txt,.docx,.doc,.md,.csv,.json,.html,.rtf"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>

          {/* File List */}
          {uploadedFiles.length > 0 && (
            <div className="files-section">
              <h4>Uploaded Files ({uploadedFiles.length})</h4>
              
              <div className="files-list">
                {uploadedFiles.map((uploadedFile, index) => (
                  <div key={index} className="file-item">
                    <div className="file-header">
                      <div className="file-info">
                        <div className="file-name">{uploadedFile.file.name}</div>
                        <div className="file-meta">
                          {formatFileSize(uploadedFile.file.size)} • {uploadedFile.file.type || 'Unknown type'}
                        </div>
                      </div>
                      
                      <div className="file-actions">
                        {uploadedFile.isAnalyzing && (
                          <div className="analyzing-indicator">
                            <svg className="spinner" viewBox="0 0 24 24">
                              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" strokeDasharray="31.416" strokeDashoffset="31.416">
                                <animate attributeName="stroke-dasharray" dur="2s" values="0 31.416;15.708 15.708;0 31.416" repeatCount="indefinite"/>
                                <animate attributeName="stroke-dashoffset" dur="2s" values="0;-15.708;-31.416" repeatCount="indefinite"/>
                              </circle>
                            </svg>
                            Analyzing...
                          </div>
                        )}
                        
                        {uploadedFile.error && (
                          <button 
                            onClick={() => retryAnalysis(index)}
                            className="retry-button"
                            title="Retry analysis"
                          >
                            ↻
                          </button>
                        )}
                        
                        <button 
                          onClick={() => removeFile(index)}
                          className="remove-button"
                          title="Remove file"
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    {uploadedFile.error && (
                      <div className="file-error">
                        <span>❌ Analysis failed: {uploadedFile.error}</span>
                      </div>
                    )}

                    {uploadedFile.analysis && (
                      <div className="analysis-results">
                        <div className="analysis-header">
                          <span className="analysis-success">✅ Analysis Complete</span>
                        </div>
                        
                        <div className="analysis-grid">
                          <div className="analysis-card">
                            <h5>File Information</h5>
                            <div className="analysis-row">
                              <span>Type:</span>
                              <span>{uploadedFile.analysis.file_type}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Size:</span>
                              <span>{formatFileSize(uploadedFile.analysis.file_size)}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Estimated Chunks:</span>
                              <span>{uploadedFile.analysis.estimated_chunks.toLocaleString()}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Processing Time:</span>
                              <span>{formatProcessingTime(uploadedFile.analysis.processing_time_estimate)}</span>
                            </div>
                          </div>

                          <div className="analysis-card">
                            <h5>Content Analysis</h5>
                            <div className="analysis-row">
                              <span>Language:</span>
                              <span>{uploadedFile.analysis.content_analysis.language}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Text Content:</span>
                              <span>{uploadedFile.analysis.content_analysis.text_content ? '✅' : '❌'}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Has Tables:</span>
                              <span>{uploadedFile.analysis.content_analysis.has_tables ? '✅' : '❌'}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Has Images:</span>
                              <span>{uploadedFile.analysis.content_analysis.has_images ? '✅' : '❌'}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Complexity Score:</span>
                              <span>{uploadedFile.analysis.content_analysis.complexity_score}/10</span>
                            </div>
                          </div>

                          <div className="analysis-card">
                            <h5>Recommended Settings</h5>
                            <div className="analysis-row">
                              <span>Chunk Size:</span>
                              <span>{uploadedFile.analysis.recommended_settings.chunk_size.toLocaleString()}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Chunk Overlap:</span>
                              <span>{uploadedFile.analysis.recommended_settings.chunk_overlap.toLocaleString()}</span>
                            </div>
                            <div className="analysis-row">
                              <span>Processing Mode:</span>
                              <span className={`mode-badge ${uploadedFile.analysis.recommended_settings.processing_mode}`}>
                                {uploadedFile.analysis.recommended_settings.processing_mode}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {uploadedFiles.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">📄</div>
              <h4>No files uploaded yet</h4>
              <p>Upload your first document to see analysis results and processing recommendations.</p>
            </div>
          )}
        </div>

        <style jsx>{`
          .file-analysis-page {
            max-width: 900px;
            margin: 0 auto;
          }

          .intro-section {
            margin-bottom: 2rem;
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

          .upload-area {
            border: 2px dashed rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            padding: 3rem 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 2rem;
            background: rgba(255, 255, 255, 0.02);
          }

          .upload-area:hover,
          .upload-area.drag-over {
            border-color: #007bff;
            background: rgba(0, 123, 255, 0.05);
            transform: translateY(-2px);
          }

          .upload-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .upload-area h4 {
            margin: 0 0 0.5rem 0;
            font-weight: 600;
            color: #ffffff;
          }

          .upload-area p {
            color: rgba(255, 255, 255, 0.7);
            margin: 0;
            font-size: 0.875rem;
          }

          .files-section {
            margin-bottom: 2rem;
          }

          .files-section h4 {
            margin: 0 0 1.5rem 0;
            font-weight: 600;
            color: #ffffff;
          }

          .files-list {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
          }

          .file-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
          }

          .file-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
          }

          .file-info {
            flex: 1;
          }

          .file-name {
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 0.25rem;
          }

          .file-meta {
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.875rem;
          }

          .file-actions {
            display: flex;
            align-items: center;
            gap: 0.75rem;
          }

          .analyzing-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #007bff;
            font-size: 0.875rem;
          }

          .spinner {
            width: 16px;
            height: 16px;
          }

          .retry-button,
          .remove-button {
            width: 32px;
            height: 32px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.875rem;
            transition: all 0.2s ease;
          }

          .retry-button {
            background: rgba(59, 130, 246, 0.2);
            color: #93c5fd;
          }

          .retry-button:hover {
            background: rgba(59, 130, 246, 0.3);
          }

          .remove-button {
            background: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
          }

          .remove-button:hover {
            background: rgba(239, 68, 68, 0.3);
          }

          .file-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 0.75rem;
            margin-bottom: 1rem;
            color: #fca5a5;
            font-size: 0.875rem;
          }

          .analysis-results {
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 1rem;
          }

          .analysis-header {
            margin-bottom: 1rem;
          }

          .analysis-success {
            color: #6ee7b7;
            font-weight: 600;
            font-size: 0.875rem;
          }

          .analysis-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
          }

          .analysis-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 1rem;
          }

          .analysis-card h5 {
            margin: 0 0 1rem 0;
            font-weight: 600;
            color: #ffffff;
            font-size: 0.875rem;
          }

          .analysis-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
          }

          .analysis-row:last-child {
            margin-bottom: 0;
          }

          .analysis-row span:first-child {
            color: rgba(255, 255, 255, 0.7);
          }

          .analysis-row span:last-child {
            color: #ffffff;
            font-weight: 500;
          }

          .mode-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
          }

          .mode-badge.streaming {
            background: rgba(16, 185, 129, 0.2);
            color: #6ee7b7;
          }

          .mode-badge.async {
            background: rgba(59, 130, 246, 0.2);
            color: #93c5fd;
          }

          .empty-state {
            text-align: center;
            padding: 3rem 2rem;
            color: rgba(255, 255, 255, 0.6);
          }

          .empty-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
          }

          .empty-state h4 {
            margin: 0 0 0.5rem 0;
            color: rgba(255, 255, 255, 0.8);
          }

          .empty-state p {
            margin: 0;
          }

          @media (max-width: 768px) {
            .file-header {
              flex-direction: column;
              align-items: flex-start;
              gap: 1rem;
            }

            .file-actions {
              align-self: flex-end;
            }

            .analysis-grid {
              grid-template-columns: 1fr;
            }

            .upload-area {
              padding: 2rem 1rem;
            }
          }
        `}</style>
      </WizardLayout>
    </>
  );
}

// Protected component with subscription paywall
const ProtectedFileAnalysisPage = withSubscriptionProtection(FileAnalysisPageContent, {
  showPaywall: true,
  blockedComponent: (
    <div className="subscription-required-page">
      <Head>
        <title>Subscription Required - WebAI Setup</title>
      </Head>
      
      <WizardLayout
        currentStep={4}
        steps={wizardSteps}
        onNext={() => {}}
        onPrevious={() => window.history.back()}
        nextDisabled={true}
        nextLabel="Subscribe Required"
      >
        <div className="subscription-block">
          <div className="block-icon">🔒</div>
          <h2>File Analysis - Premium Feature</h2>
          <p>
            Upload and analyze your documents to get personalized processing recommendations.
            This feature is available to subscribers only.
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

// Main export component
export default function FileAnalysisPage() {
  return (
    <PaywallProvider autoCheckSubscription={true} debugMode={process.env.NODE_ENV === 'development'}>
      <ProtectedFileAnalysisPage />
    </PaywallProvider>
  );
}