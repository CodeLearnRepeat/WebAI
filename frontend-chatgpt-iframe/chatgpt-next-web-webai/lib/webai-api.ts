/**
 * WebAI API Adapter for ChatGPT-Next-Web
 * 
 * Integrates ChatGPT-Next-Web with WebAI FastAPI backend
 * Handles streaming responses, RAG parameters, and tenant authentication
 */

export interface WebAIConfig {
  apiUrl: string;
  tenantId: string;
  sessionId: string;
  useRAG: boolean;
  ragTopK: number;
  title?: string;
  debug?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  id?: string;
  timestamp?: number;
}

export interface StreamResponse {
  role: 'assistant';
  content: string;
  delta: boolean;
  finished?: boolean;
  error?: string;
}

export class WebAIApi {
  protected config: WebAIConfig;
  protected abortController: AbortController | null = null;

  constructor(config: WebAIConfig) {
    this.config = config;
    this.debugLog('WebAI API initialized with config:', config);
  }

  protected debugLog(...args: any[]) {
    if (this.config.debug) {
      console.log('[WebAI API]', ...args);
    }
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<WebAIConfig>) {
    this.config = { ...this.config, ...newConfig };
    this.debugLog('Config updated:', this.config);
  }

  /**
   * Stream chat completion from WebAI FastAPI backend
   */
  async *chat(messages: ChatMessage[]): AsyncGenerator<StreamResponse, void, unknown> {
    const lastMessage = messages[messages.length - 1];
    
    if (!lastMessage || lastMessage.role !== 'user') {
      throw new Error('Last message must be from user');
    }

    // Cancel any existing request
    if (this.abortController) {
      this.abortController.abort();
    }
    
    this.abortController = new AbortController();
    
    const requestBody = {
      message: lastMessage.content,
      session_id: this.config.sessionId,
      use_redis_conversations: true,
      use_rag: this.config.useRAG,
      rag_top_k: this.config.ragTopK,
    };

    this.debugLog('Sending chat request:', requestBody);

    try {
      const response = await fetch(`${this.config.apiUrl}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': this.config.tenantId,
        },
        body: JSON.stringify(requestBody),
        signal: this.abortController.signal,
      });

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

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body available');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete lines
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex).trimEnd();
          buffer = buffer.slice(newlineIndex + 1);

          if (!line.startsWith('data: ')) continue;
          
          const data = line.slice(6).trim();
          if (data === '[DONE]') {
            this.debugLog('Stream completed, full response length:', fullResponse.length);
            yield {
              role: 'assistant',
              content: '',
              delta: false,
              finished: true
            };
            return;
          }

          try {
            const parsed = JSON.parse(data);
            
            if (parsed.error) {
              throw new Error(parsed.error);
            }

            const content = parsed.choices?.[0]?.delta?.content;
            if (content) {
              fullResponse += content;
              this.debugLog('Received delta:', content.length, 'chars');
              
              yield {
                role: 'assistant',
                content,
                delta: true
              };
            }
          } catch (parseError) {
            // Skip invalid JSON, but log if debugging
            if (this.config.debug && !(parseError instanceof SyntaxError)) {
              console.warn('[WebAI API] Parse error:', parseError, 'for data:', data);
            }
          }
        }
      }

    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          this.debugLog('Request aborted');
          return;
        }
        
        this.debugLog('Chat error:', error.message);
        yield {
          role: 'assistant',
          content: '',
          delta: false,
          error: error.message
        };
      } else {
        this.debugLog('Unknown error:', error);
        yield {
          role: 'assistant',
          content: '',
          delta: false,
          error: 'An unknown error occurred'
        };
      }
    } finally {
      this.abortController = null;
    }
  }

  /**
   * Cancel ongoing request
   */
  cancel() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
      this.debugLog('Request cancelled');
    }
  }

  /**
   * Test connection to WebAI backend
   */
  async testConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.apiUrl}/health`, {
        method: 'GET',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
      });
      
      const isHealthy = response.ok;
      this.debugLog('Connection test:', isHealthy ? 'SUCCESS' : 'FAILED');
      return isHealthy;
    } catch (error) {
      this.debugLog('Connection test error:', error);
      return false;
    }
  }

  /**
   * Get tenant configuration
   */
  async getTenantConfig(): Promise<any> {
    try {
      const response = await fetch(`${this.config.apiUrl}/tenants/${this.config.tenantId}`, {
        method: 'GET',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to get tenant config: ${response.statusText}`);
      }
      
      const config = await response.json();
      this.debugLog('Tenant config:', config);
      return config;
    } catch (error) {
      this.debugLog('Failed to get tenant config:', error);
      throw error;
    }
  }

  /**
   * Get conversation history
   */
  async getConversationHistory(): Promise<ChatMessage[]> {
    try {
      const response = await fetch(`${this.config.apiUrl}/conversations/${this.config.sessionId}`, {
        method: 'GET',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
      });
      
      if (!response.ok) {
        this.debugLog('No conversation history available');
        return [];
      }
      
      const history = await response.json();
      this.debugLog('Loaded conversation history:', history.length, 'messages');
      return history;
    } catch (error) {
      this.debugLog('Failed to load conversation history:', error);
      return [];
    }
  }

  /**
   * Clear conversation history
   */
  async clearConversationHistory(): Promise<void> {
    try {
      const response = await fetch(`${this.config.apiUrl}/conversations/${this.config.sessionId}`, {
        method: 'DELETE',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to clear conversation: ${response.statusText}`);
      }
      
      this.debugLog('Conversation history cleared');
    } catch (error) {
      this.debugLog('Failed to clear conversation history:', error);
      throw error;
    }
  }
}

/**
 * Helper function to create WebAI API instance from URL parameters
 */
export function createWebAIFromParams(): WebAIApi | null {
  const params = new URLSearchParams(window.location.search);
  
  const embedded = params.get('embedded');
  if (embedded !== 'true') {
    return null;
  }

  // Access environment variable in Next.js client-side
  const apiUrl = 'https://web3ai-backend-v67-api-180395924844.us-central1.run.app';

  const config: WebAIConfig = {
    apiUrl,
    tenantId: params.get('tenant') || 'default',
    sessionId: params.get('session') || 'default',
    useRAG: params.get('rag') === 'true',
    ragTopK: parseInt(params.get('rag_top_k') || '4'),
    debug: params.get('debug') === 'true'
  };

  return new WebAIApi(config);
}

/**
 * Tenant Setup Types - Updated to match backend schema
 */
export interface TenantRegistrationData {
  openrouter_api_key: string;
  system_prompt: string;
  allowed_domains: string[];
  model?: string;
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
  rag?: RagConfig;
}

export interface RagMilvusConfig {
  uri: string;
  token?: string;
  db_name?: string;
  collection: string;
  vector_field?: string;
  text_field?: string;
  metadata_field?: string;
  metric_type?: 'IP' | 'COSINE' | 'L2';
}

export interface RagConfig {
  enabled?: boolean;
  self_rag_enabled?: boolean;
  provider?: 'milvus';
  milvus?: RagMilvusConfig;
  embedding_provider?: 'sentence_transformers' | 'openai' | 'voyageai';
  embedding_model?: string;
  provider_keys?: Record<string, string>;
  top_k?: number;
}

export interface SystemCapabilities {
  features: {
    rag_processing: boolean;
    streaming_ingestion: boolean;
    batch_processing: boolean;
    hybrid_search: boolean;
  };
  limits: {
    max_file_size_mb: number;
    max_concurrent_jobs: number;
    supported_formats: string[];
    max_chunk_size: number;
  };
  resources: {
    embedding_models: string[];
    vector_stores: string[];
    processing_modes: string[];
  };
}

export interface FileAnalysisRequest {
  tenant_id: string;
  filename: string;
  file_size: number;
  content_preview?: string;
}

export interface FileAnalysisResult {
  filename: string;
  file_size: number;
  estimated_chunks: number;
  processing_time_estimate: string;
  recommended_settings: {
    chunk_size: number;
    chunk_overlap: number;
    processing_mode: 'streaming' | 'async';
  };
  file_type: string;
  content_analysis: {
    text_content: boolean;
    has_tables: boolean;
    has_images: boolean;
    language: string;
    complexity_score: number;
  };
}

export interface ProcessingSchema {
  chunk_size: number;
  chunk_overlap: number;
  processing_mode: 'streaming' | 'async';
  metadata_extraction: boolean;
  enable_ocr: boolean;
  custom_fields?: Record<string, any>;
}

export interface ProcessingProgress {
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  current_stage: string;
  chunks_processed: number;
  total_chunks: number;
  estimated_completion: string;
  error_message?: string;
}

/**
 * Extended WebAI API class with tenant setup methods
 */
export class WebAITenantSetupApi extends WebAIApi {
  /**
   * Register a new tenant
   */
  async registerTenant(tenantData: TenantRegistrationData): Promise<{ tenant_id: string; message: string }> {
    try {
      // Get admin key from environment - must be set
      const adminKey = process.env.NEXT_PUBLIC_WEBAI_ADMIN_KEY;
      if (!adminKey) {
        throw new Error('NEXT_PUBLIC_WEBAI_ADMIN_KEY environment variable is required');
      }
      
      const response = await fetch(`${this.config.apiUrl}/register-tenant`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Key': adminKey,
        },
        body: JSON.stringify(tenantData),
      });

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

      const result = await response.json();
      this.debugLog('Tenant registered successfully:', result);
      return result;
    } catch (error) {
      this.debugLog('Failed to register tenant:', error);
      throw error;
    }
  }

  /**
   * Validate OpenRouter API key
   */
  async validateOpenRouterKey(apiKey: string): Promise<{ valid: boolean; models?: string[] }> {
    try {
      const response = await fetch(`${this.config.apiUrl}/api-keys/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': this.config.tenantId,
        },
        body: JSON.stringify({
          api_key: apiKey,
          provider: 'openrouter'
        }),
      });

      if (!response.ok) {
        throw new Error(`Validation failed: ${response.statusText}`);
      }

      const result = await response.json();
      this.debugLog('API key validation result:', result);
      return result;
    } catch (error) {
      this.debugLog('Failed to validate API key:', error);
      throw error;
    }
  }

  /**
   * Get system processing capabilities
   */
  async getSystemCapabilities(): Promise<SystemCapabilities> {
    try {
      const response = await fetch(`${this.config.apiUrl}/rag/processing-capabilities`, {
        method: 'GET',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get capabilities: ${response.statusText}`);
      }

      const capabilities = await response.json();
      this.debugLog('System capabilities:', capabilities);
      return capabilities;
    } catch (error) {
      this.debugLog('Failed to get system capabilities:', error);
      throw error;
    }
  }

  /**
   * Analyze file for processing recommendations
   */
  async analyzeFile(file: File): Promise<FileAnalysisResult> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tenant_id', this.config.tenantId);

      const response = await fetch(`${this.config.apiUrl}/rag/analyze-file`, {
        method: 'POST',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`File analysis failed: ${response.statusText}`);
      }

      const result = await response.json();
      this.debugLog('File analysis result:', result);
      return result;
    } catch (error) {
      this.debugLog('Failed to analyze file:', error);
      throw error;
    }
  }

  /**
   * Process file with streaming progress
   */
  async *processFileStreaming(
    file: File,
    schema: ProcessingSchema
  ): AsyncGenerator<ProcessingProgress, void, unknown> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tenant_id', this.config.tenantId);
      formData.append('schema_config', JSON.stringify(schema));

      const response = await fetch(`${this.config.apiUrl}/rag/ingest-file-streaming`, {
        method: 'POST',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`File processing failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body available');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex).trimEnd();
          buffer = buffer.slice(newlineIndex + 1);

          if (!line.startsWith('data: ')) continue;
          
          const data = line.slice(6).trim();
          if (data === '[DONE]') {
            this.debugLog('File processing completed');
            return;
          }

          try {
            const progress = JSON.parse(data);
            this.debugLog('Processing progress:', progress);
            yield progress;
          } catch (parseError) {
            // Skip invalid JSON
            if (this.config.debug) {
              console.warn('[WebAI API] Parse error:', parseError, 'for data:', data);
            }
          }
        }
      }
    } catch (error) {
      this.debugLog('Failed to process file:', error);
      throw error;
    }
  }

  /**
   * Process file asynchronously (background processing)
   */
  async processFileAsync(
    file: File,
    schema: ProcessingSchema
  ): Promise<{ job_id: string; status: string }> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tenant_id', this.config.tenantId);
      formData.append('schema_config', JSON.stringify(schema));

      const response = await fetch(`${this.config.apiUrl}/rag/ingest-file-async`, {
        method: 'POST',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Async processing failed: ${response.statusText}`);
      }

      const result = await response.json();
      this.debugLog('Async processing started:', result);
      return result;
    } catch (error) {
      this.debugLog('Failed to start async processing:', error);
      throw error;
    }
  }

  /**
   * Get processing job status
   */
  async getProcessingStatus(jobId: string): Promise<ProcessingProgress> {
    try {
      const response = await fetch(`${this.config.apiUrl}/rag/job-status/${jobId}`, {
        method: 'GET',
        headers: {
          'X-Tenant-ID': this.config.tenantId,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get job status: ${response.statusText}`);
      }

      const status = await response.json();
      this.debugLog('Job status:', status);
      return status;
    } catch (error) {
      this.debugLog('Failed to get job status:', error);
      throw error;
    }
  }
}

/**
 * Helper function to create tenant setup API instance from URL parameters
 */
export function createTenantSetupApi(): WebAITenantSetupApi | null {
  const params = new URLSearchParams(window.location.search);
  
  // Access environment variable in Next.js client-side
  const apiUrl = process.env.NEXT_PUBLIC_WEBAI_API_URL || 'https://web3ai-backend-v65-api-180395924844.us-central1.run.app';

  const config: WebAIConfig = {
    apiUrl,
    tenantId: params.get('tenant') || 'setup',
    sessionId: params.get('session') || 'setup',
    useRAG: false,
    ragTopK: 4,
    debug: params.get('debug') === 'true'
  };

  return new WebAITenantSetupApi(config);
}