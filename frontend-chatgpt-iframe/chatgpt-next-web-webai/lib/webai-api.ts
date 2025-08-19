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
  private config: WebAIConfig;
  private abortController: AbortController | null = null;

  constructor(config: WebAIConfig) {
    this.config = config;
    this.debugLog('WebAI API initialized with config:', config);
  }

  private debugLog(...args: any[]) {
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
  const apiUrl = process.env.NEXT_PUBLIC_WEBAI_API_URL || 'https://your-webai-backend.run.app';
  if (!apiUrl) {
    console.error('NEXT_PUBLIC_WEBAI_API_URL environment variable is required');
    return null;
  }

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