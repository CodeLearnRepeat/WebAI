/**
 * Step 5: File Processing Page
 * Schema configuration interface and file processing with progress monitoring
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import WizardLayout, { WizardStep } from '../../components/setup/WizardLayout';
import { 
  WebAITenantSetupApi, 
  ProcessingSchema, 
  ProcessingProgress, 
  FileAnalysisResult,
  createTenantSetupApi 
} from '../../lib/webai-api';

const wizardSteps: WizardStep[] = [
  { id: 1, title: 'Welcome', description: 'Introduction to setup', path: '/setup/step1', completed: true },
  { id: 2, title: 'Tenant Registration', description: 'Configure your tenant settings', path: '/setup/step2', completed: true },
  { id: 3, title: 'System Capabilities', description: 'Review available features', path: '/setup/step3', completed: true },
  { id: 4, title: 'File Analysis', description: 'Upload and analyze files', path: '/setup/step4', completed: true },
  { id: 5, title: 'File Processing', description: 'Configure processing pipeline', path: '/setup/step5' },
];

interface FileWithAnalysis {
  file: File;
  analysis: FileAnalysisResult;
}

interface ProcessingJob {
  file: File;
  jobId?: string;
  progress: ProcessingProgress;
  error?: string;
}

export default function FileProcessingPage() {
  const router = useRouter();
  const [api, setApi] = useState<WebAITenantSetupApi | null>(null);
  const [files, setFiles] = useState<FileWithAnalysis[]>([]);
  const [processingJobs, setProcessingJobs] = useState<ProcessingJob[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [allProcessingComplete, setAllProcessingComplete] = useState(false);

  const [schema, setSchema] = useState<ProcessingSchema>({
    chunk_size: 1000,
    chunk_overlap: 200,
    processing_mode: 'streaming',
    metadata_extraction: true,
    enable_ocr: false,
    custom_fields: {}
  });

  useEffect(() => {
    const setupApi = createTenantSetupApi();
    setApi(setupApi);

    // Load files from previous step
    const savedResults = sessionStorage.getItem('fileAnalysisResults');
    if (savedResults) {
      try {
        const results = JSON.parse(savedResults);
        setFiles(results);
        
        // Set initial schema based on first file's recommendations
        if (results.length > 0) {
          const firstAnalysis = results[0].analysis;
          setSchema(prev => ({
            ...prev,
            chunk_size: firstAnalysis.recommended_settings.chunk_size,
            chunk_overlap: firstAnalysis.recommended_settings.chunk_overlap,
            processing_mode: firstAnalysis.recommended_settings.processing_mode,
          }));
        }
      } catch (error) {
        console.error('Failed to load file analysis results:', error);
      }
    }
  }, []);

  const handleSchemaChange = (field: keyof ProcessingSchema, value: any) => {
    setSchema(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleCustomFieldChange = (key: string, value: string) => {
    setSchema(prev => ({
      ...prev,
      custom_fields: {
        ...prev.custom_fields,
        [key]: value,
      },
    }));
  };

  const addCustomField = () => {
    const key = prompt('Enter custom field name:');
    if (key && key.trim()) {
      handleCustomFieldChange(key.trim(), '');
    }
  };

  const removeCustomField = (key: string) => {
    setSchema(prev => ({
      ...prev,
      custom_fields: Object.fromEntries(
        Object.entries(prev.custom_fields || {}).filter(([k]) => k !== key)
      ),
    }));
  };

  const startProcessing = async () => {
    if (!api || files.length === 0) return;

    setIsProcessing(true);
    const jobs: ProcessingJob[] = files.map(({ file }) => ({
      file,
      progress: {
        status: 'queued',
        progress_percentage: 0,
        current_stage: 'Initializing',
        chunks_processed: 0,
        total_chunks: 0,
        estimated_completion: 'Calculating...',
      },
    }));

    setProcessingJobs(jobs);

    // Process files based on selected mode
    if (schema.processing_mode === 'streaming') {
      await processFilesStreaming(jobs);
    } else {
      await processFilesAsync(jobs);
    }
  };

  const processFilesStreaming = async (jobs: ProcessingJob[]) => {
    if (!api) return;

    for (let i = 0; i < jobs.length; i++) {
      const job = jobs[i];
      
      try {
        setProcessingJobs(prev => 
          prev.map((j, index) => 
            index === i ? { ...j, progress: { ...j.progress, status: 'processing' } } : j
          )
        );

        const progressGenerator = api.processFileStreaming(job.file, schema);
        
        for await (const progress of progressGenerator) {
          setProcessingJobs(prev => 
            prev.map((j, index) => 
              index === i ? { ...j, progress } : j
            )
          );
        }

        // Mark as completed
        setProcessingJobs(prev => 
          prev.map((j, index) => 
            index === i ? { 
              ...j, 
              progress: { 
                ...j.progress, 
                status: 'completed', 
                progress_percentage: 100 
              } 
            } : j
          )
        );

      } catch (error) {
        console.error(`Failed to process file ${job.file.name}:`, error);
        setProcessingJobs(prev => 
          prev.map((j, index) => 
            index === i ? { 
              ...j, 
              progress: { ...j.progress, status: 'failed' },
              error: error instanceof Error ? error.message : 'Processing failed'
            } : j
          )
        );
      }
    }

    checkAllProcessingComplete();
  };

  const processFilesAsync = async (jobs: ProcessingJob[]) => {
    if (!api) return;

    // Start all async jobs
    const jobPromises = jobs.map(async (job, index) => {
      try {
        const result = await api.processFileAsync(job.file, schema);
        
        setProcessingJobs(prev => 
          prev.map((j, i) => 
            i === index ? { 
              ...j, 
              jobId: result.job_id,
              progress: { ...j.progress, status: 'processing' }
            } : j
          )
        );

        // Poll for progress
        await pollJobProgress(index, result.job_id);

      } catch (error) {
        console.error(`Failed to start processing for ${job.file.name}:`, error);
        setProcessingJobs(prev => 
          prev.map((j, i) => 
            i === index ? { 
              ...j, 
              progress: { ...j.progress, status: 'failed' },
              error: error instanceof Error ? error.message : 'Failed to start processing'
            } : j
          )
        );
      }
    });

    await Promise.all(jobPromises);
    checkAllProcessingComplete();
  };

  const pollJobProgress = async (jobIndex: number, jobId: string) => {
    if (!api) return;

    const pollInterval = setInterval(async () => {
      try {
        const progress = await api.getProcessingStatus(jobId);
        
        setProcessingJobs(prev => 
          prev.map((j, i) => 
            i === jobIndex ? { ...j, progress } : j
          )
        );

        if (progress.status === 'completed' || progress.status === 'failed') {
          clearInterval(pollInterval);
          
          if (progress.status === 'failed') {
            setProcessingJobs(prev => 
              prev.map((j, i) => 
                i === jobIndex ? { 
                  ...j, 
                  error: progress.error_message || 'Processing failed'
                } : j
              )
            );
          }
        }
      } catch (error) {
        console.error('Failed to get job status:', error);
        clearInterval(pollInterval);
        
        setProcessingJobs(prev => 
          prev.map((j, i) => 
            i === jobIndex ? { 
              ...j, 
              progress: { ...j.progress, status: 'failed' },
              error: 'Failed to get progress updates'
            } : j
          )
        );
      }
    }, 2000); // Poll every 2 seconds
  };

  const checkAllProcessingComplete = () => {
    setIsProcessing(false);
    const allComplete = processingJobs.every(job => 
      job.progress.status === 'completed' || job.progress.status === 'failed'
    );
    setAllProcessingComplete(allComplete);
  };

  const handleFinish = () => {
    // Clear session storage
    sessionStorage.removeItem('fileAnalysisResults');
    // Redirect to chat with setup complete
    router.push('/embedded/chat' + window.location.search + '&setup=complete');
  };

  const handlePrevious = () => {
    router.push('/setup/step4' + window.location.search);
  };

  const getOverallProgress = () => {
    if (processingJobs.length === 0) return 0;
    const totalProgress = processingJobs.reduce((sum, job) => sum + job.progress.progress_percentage, 0);
    return totalProgress / processingJobs.length;
  };

  const hasCompletedJobs = processingJobs.some(job => job.progress.status === 'completed');
  const hasFailedJobs = processingJobs.some(job => job.progress.status === 'failed');

  return (
    <>
      <Head>
        <title>File Processing - WebAI Setup</title>
      </Head>

      <WizardLayout
        currentStep={5}
        steps={wizardSteps}
        onNext={allProcessingComplete ? handleFinish : undefined}
        onPrevious={!isProcessing ? handlePrevious : undefined}
        nextDisabled={!allProcessingComplete}
        nextLabel={allProcessingComplete ? 'Complete Setup' : 'Processing...'}
        showNext={processingJobs.length > 0}
        showPrevious={!isProcessing}
      >
        <div className="processing-page">
          <div className="intro-section">
            <h3>File Processing Configuration</h3>
            <p>Configure how your files will be processed and ingested into the knowledge base.</p>
          </div>

          {files.length === 0 && (
            <div className="no-files-message">
              <div className="message-icon">📄</div>
              <h4>No files to process</h4>
              <p>Go back to the previous step to upload and analyze files first.</p>
            </div>
          )}

          {files.length > 0 && !isProcessing && processingJobs.length === 0 && (
            <div className="configuration-section">
              <div className="files-summary">
                <h4>Files to Process ({files.length})</h4>
                <div className="files-list">
                  {files.map((fileData, index) => (
                    <div key={index} className="file-summary">
                      <div className="file-icon">📄</div>
                      <div className="file-info">
                        <div className="file-name">{fileData.file.name}</div>
                        <div className="file-details">
                          {(fileData.file.size / 1024 / 1024).toFixed(1)} MB • 
                          {fileData.analysis.estimated_chunks.toLocaleString()} chunks
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="schema-configuration">
                <h4>Processing Configuration</h4>
                
                <div className="config-grid">
                  <div className="config-group">
                    <label htmlFor="chunk_size">Chunk Size</label>
                    <input
                      id="chunk_size"
                      type="number"
                      value={schema.chunk_size}
                      onChange={(e) => handleSchemaChange('chunk_size', parseInt(e.target.value))}
                      min="100"
                      max="4000"
                    />
                    <small>Number of characters per document chunk</small>
                  </div>

                  <div className="config-group">
                    <label htmlFor="chunk_overlap">Chunk Overlap</label>
                    <input
                      id="chunk_overlap"
                      type="number"
                      value={schema.chunk_overlap}
                      onChange={(e) => handleSchemaChange('chunk_overlap', parseInt(e.target.value))}
                      min="0"
                      max="1000"
                    />
                    <small>Overlapping characters between chunks</small>
                  </div>

                  <div className="config-group">
                    <label htmlFor="processing_mode">Processing Mode</label>
                    <select
                      id="processing_mode"
                      value={schema.processing_mode}
                      onChange={(e) => handleSchemaChange('processing_mode', e.target.value as 'streaming' | 'async')}
                    >
                      <option value="streaming">Real-time Streaming</option>
                      <option value="async">Background Processing</option>
                    </select>
                    <small>
                      {schema.processing_mode === 'streaming' 
                        ? 'Process files in real-time with live progress updates'
                        : 'Process files in the background (recommended for large files)'
                      }
                    </small>
                  </div>
                </div>

                <div className="config-options">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={schema.metadata_extraction}
                      onChange={(e) => handleSchemaChange('metadata_extraction', e.target.checked)}
                    />
                    <span>Extract Metadata</span>
                    <small>Extract document metadata like titles, authors, dates</small>
                  </label>

                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={schema.enable_ocr}
                      onChange={(e) => handleSchemaChange('enable_ocr', e.target.checked)}
                    />
                    <span>Enable OCR</span>
                    <small>Extract text from images and scanned documents</small>
                  </label>
                </div>

                <div className="custom-fields">
                  <div className="custom-fields-header">
                    <h5>Custom Metadata Fields</h5>
                    <button onClick={addCustomField} className="add-field-button">
                      + Add Field
                    </button>
                  </div>
                  
                  {Object.keys(schema.custom_fields || {}).length > 0 && (
                    <div className="custom-fields-list">
                      {Object.entries(schema.custom_fields || {}).map(([key, value]) => (
                        <div key={key} className="custom-field">
                          <input
                            type="text"
                            value={key}
                            disabled
                            className="field-name"
                          />
                          <input
                            type="text"
                            value={value as string}
                            onChange={(e) => handleCustomFieldChange(key, e.target.value)}
                            placeholder="Field value"
                            className="field-value"
                          />
                          <button 
                            onClick={() => removeCustomField(key)}
                            className="remove-field-button"
                          >
                            ✕
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="start-processing">
                  <button
                    onClick={startProcessing}
                    className="start-button"
                    disabled={files.length === 0}
                  >
                    Start Processing ({files.length} file{files.length !== 1 ? 's' : ''})
                  </button>
                </div>
              </div>
            </div>
          )}

          {(isProcessing || processingJobs.length > 0) && (
            <div className="processing-section">
              <div className="processing-header">
                <h4>Processing Progress</h4>
                {isProcessing && (
                  <div className="overall-progress">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${getOverallProgress()}%` }}
                      />
                    </div>
                    <span className="progress-text">
                      {getOverallProgress().toFixed(1)}% Complete
                    </span>
                  </div>
                )}
              </div>

              <div className="jobs-list">
                {processingJobs.map((job, index) => (
                  <div key={index} className={`job-item ${job.progress.status}`}>
                    <div className="job-header">
                      <div className="job-info">
                        <div className="job-name">{job.file.name}</div>
                        <div className="job-stage">{job.progress.current_stage}</div>
                      </div>
                      <div className="job-status">
                        {job.progress.status === 'processing' && (
                          <div className="processing-spinner">
                            <svg className="spinner" viewBox="0 0 24 24">
                              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" strokeDasharray="31.416" strokeDashoffset="31.416">
                                <animate attributeName="stroke-dasharray" dur="2s" values="0 31.416;15.708 15.708;0 31.416" repeatCount="indefinite"/>
                                <animate attributeName="stroke-dashoffset" dur="2s" values="0;-15.708;-31.416" repeatCount="indefinite"/>
                              </circle>
                            </svg>
                          </div>
                        )}
                        {job.progress.status === 'completed' && <span className="status-icon completed">✅</span>}
                        {job.progress.status === 'failed' && <span className="status-icon failed">❌</span>}
                        {job.progress.status === 'queued' && <span className="status-icon queued">⏳</span>}
                      </div>
                    </div>

                    <div className="job-progress">
                      <div className="progress-bar">
                        <div 
                          className="progress-fill"
                          style={{ width: `${job.progress.progress_percentage}%` }}
                        />
                      </div>
                      <div className="progress-details">
                        <span>{job.progress.progress_percentage.toFixed(1)}%</span>
                        {job.progress.chunks_processed > 0 && (
                          <span>
                            {job.progress.chunks_processed.toLocaleString()} / {job.progress.total_chunks.toLocaleString()} chunks
                          </span>
                        )}
                        {job.progress.estimated_completion && job.progress.status === 'processing' && (
                          <span>ETA: {job.progress.estimated_completion}</span>
                        )}
                      </div>
                    </div>

                    {job.error && (
                      <div className="job-error">
                        ❌ {job.error}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {allProcessingComplete && (
                <div className="completion-summary">
                  <div className="summary-icon">
                    {hasFailedJobs ? '⚠️' : '🎉'}
                  </div>
                  <h4>
                    {hasFailedJobs ? 'Processing Complete with Errors' : 'All Files Processed Successfully!'}
                  </h4>
                  <p>
                    {hasCompletedJobs && `${processingJobs.filter(j => j.progress.status === 'completed').length} files processed successfully. `}
                    {hasFailedJobs && `${processingJobs.filter(j => j.progress.status === 'failed').length} files failed to process.`}
                  </p>
                  {hasCompletedJobs && (
                    <p>Your knowledge base is ready! You can now use the chat interface with RAG capabilities.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <style jsx>{`
          .processing-page {
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

          .no-files-message {
            text-align: center;
            padding: 4rem 2rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
          }

          .message-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
          }

          .no-files-message h4 {
            margin: 0 0 0.5rem 0;
            color: rgba(255, 255, 255, 0.8);
          }

          .no-files-message p {
            margin: 0;
            color: rgba(255, 255, 255, 0.6);
          }

          .configuration-section {
            display: flex;
            flex-direction: column;
            gap: 2rem;
          }

          .files-summary {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
          }

          .files-summary h4 {
            margin: 0 0 1rem 0;
            font-weight: 600;
            color: #ffffff;
          }

          .files-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
          }

          .file-summary {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
          }

          .file-icon {
            font-size: 1.5rem;
          }

          .file-info {
            flex: 1;
          }

          .file-name {
            font-weight: 500;
            color: #ffffff;
            margin-bottom: 0.25rem;
          }

          .file-details {
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.6);
          }

          .schema-configuration {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
          }

          .schema-configuration h4 {
            margin: 0 0 1.5rem 0;
            font-weight: 600;
            color: #ffffff;
          }

          .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
          }

          .config-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
          }

          .config-group label {
            font-weight: 500;
            color: #ffffff;
          }

          .config-group input,
          .config-group select {
            padding: 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #ffffff;
            font-size: 0.875rem;
          }

          .config-group input:focus,
          .config-group select:focus {
            outline: none;
            border-color: #007bff;
            background: rgba(255, 255, 255, 0.1);
          }

          .config-group small {
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.75rem;
          }

          .config-options {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-bottom: 2rem;
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
            font-size: 0.75rem;
          }

          .custom-fields {
            margin-bottom: 2rem;
          }

          .custom-fields-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
          }

          .custom-fields-header h5 {
            margin: 0;
            font-weight: 600;
            color: #ffffff;
          }

          .add-field-button {
            padding: 0.5rem 1rem;
            background: rgba(0, 123, 255, 0.2);
            border: 1px solid rgba(0, 123, 255, 0.3);
            border-radius: 6px;
            color: #93c5fd;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .add-field-button:hover {
            background: rgba(0, 123, 255, 0.3);
          }

          .custom-fields-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
          }

          .custom-field {
            display: flex;
            gap: 0.75rem;
            align-items: center;
          }

          .field-name {
            flex: 1;
            background: rgba(255, 255, 255, 0.1) !important;
            opacity: 0.7;
          }

          .field-value {
            flex: 2;
          }

          .remove-field-button {
            width: 32px;
            height: 32px;
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            color: #fca5a5;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .remove-field-button:hover {
            background: rgba(239, 68, 68, 0.3);
          }

          .start-processing {
            text-align: center;
          }

          .start-button {
            padding: 1rem 2rem;
            background: #007bff;
            border: none;
            border-radius: 8px;
            color: #ffffff;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .start-button:hover:not(:disabled) {
            background: #0056b3;
            transform: translateY(-2px);
          }

          .start-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
          }

          .processing-section {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
          }

          .processing-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
          }

          .processing-header h4 {
            margin: 0;
            font-weight: 600;
            color: #ffffff;
          }

          .overall-progress {
            display: flex;
            align-items: center;
            gap: 1rem;
            min-width: 200px;
          }

          .progress-bar {
            flex: 1;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
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

          .jobs-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-bottom: 2rem;
          }

          .job-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 1rem;
          }

          .job-item.completed {
            border-color: rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.05);
          }

          .job-item.failed {
            border-color: rgba(239, 68, 68, 0.3);
            background: rgba(239, 68, 68, 0.05);
          }

          .job-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.75rem;
          }

          .job-info {
            flex: 1;
          }

          .job-name {
            font-weight: 500;
            color: #ffffff;
            margin-bottom: 0.25rem;
          }

          .job-stage {
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.6);
          }

          .job-status {
            display: flex;
            align-items: center;
          }

          .processing-spinner {
            width: 20px;
            height: 20px;
          }

          .spinner {
            width: 100%;
            height: 100%;
            color: #007bff;
          }

          .status-icon {
            font-size: 1.25rem;
          }

          .job-progress {
            margin-bottom: 0.5rem;
          }

          .progress-details {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.5rem;
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.7);
          }

          .job-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 0.75rem;
            color: #fca5a5;
            font-size: 0.875rem;
          }

          .completion-summary {
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
          }

          .summary-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
          }

          .completion-summary h4 {
            margin: 0 0 1rem 0;
            color: #ffffff;
          }

          .completion-summary p {
            margin: 0 0 0.5rem 0;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.5;
          }

          @media (max-width: 768px) {
            .config-grid {
              grid-template-columns: 1fr;
            }

            .processing-header {
              flex-direction: column;
              align-items: flex-start;
              gap: 1rem;
            }

            .overall-progress {
              min-width: auto;
              width: 100%;
            }

            .job-header {
              flex-direction: column;
              align-items: flex-start;
              gap: 0.5rem;
            }

            .progress-details {
              flex-direction: column;
              align-items: flex-start;
              gap: 0.25rem;
            }

            .custom-field {
              flex-direction: column;
              align-items: stretch;
            }

            .field-name,
            .field-value {
              flex: none;
            }
          }
        `}</style>
      </WizardLayout>
    </>
  );
}