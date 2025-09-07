/**
 * React Hook for WebAI Integration
 * 
 * Manages WebAI API connection, configuration, and cross-origin communication
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { WebAIApi, WebAIConfig, ChatMessage, createWebAIFromParams } from '@/lib/webai-api';

export interface WebAIState {
  api: WebAIApi | null;
  config: WebAIConfig | null;
  isEmbedded: boolean;
  isReady: boolean;
  isConnected: boolean;
  error: string | null;
}

export interface WebAIActions {
  updateConfig: (config: Partial<WebAIConfig>) => void;
  testConnection: () => Promise<boolean>;
  sendMessage: (message: string) => void;
  clearConversation: () => Promise<void>;
  sendToParent: (type: string, data?: any) => void;
}

export interface UseWebAIResult extends WebAIState, WebAIActions {}

export function useWebAI(): UseWebAIResult {
  const [state, setState] = useState<WebAIState>({
    api: null,
    config: null,
    isEmbedded: false,
    isReady: false,
    isConnected: false,
    error: null
  });

  const messageHandlersRef = useRef<Map<string, (data: any) => void>>(new Map());
  const parentOriginRef = useRef<string | null>(null);

  // Initialize WebAI API from URL parameters or parent messages
  useEffect(() => {
    const isEmbedded = new URLSearchParams(window.location.search).get('embedded') === 'true';
    
    setState(prev => ({ ...prev, isEmbedded }));

    if (isEmbedded) {
      // Create config from URL parameters
      const params = new URLSearchParams(window.location.search);
      const urlConfig: WebAIConfig = {
        apiUrl: getApiUrl(),
        tenantId: params.get('tenant') || 'default',
        sessionId: params.get('session') || 'default',
        useRAG: params.get('rag') === 'true',
        ragTopK: parseInt(params.get('rag_top_k') || '4'),
        title: params.get('title') || 'AI Assistant',
        debug: params.get('debug') === 'true'
      };
      
      const api = new WebAIApi(urlConfig);
      setState(prev => ({
        ...prev,
        api,
        config: urlConfig,
        isReady: true
      }));
    }
  }, []);

  // Cross-origin communication setup
  useEffect(() => {
    if (!state.isEmbedded) return;

    const handleMessage = (event: MessageEvent) => {
      // Store parent origin for sending messages back
      if (!parentOriginRef.current && event.origin !== window.location.origin) {
        parentOriginRef.current = event.origin;
      }

      const { type, data } = event.data;

      // Handle specific message types
      switch (type) {
        case 'INIT_CONFIG':
          handleInitConfig(data);
          break;
        case 'UPDATE_CONFIG':
          handleUpdateConfig(data);
          break;
        case 'SEND_MESSAGE':
          handleSendMessage(data);
          break;
        case 'FOCUS_REQUEST':
          handleFocusRequest();
          break;
        case 'PAGE_VISIBLE':
          handlePageVisible();
          break;
        case 'WINDOW_RESIZE':
          handleWindowResize(data);
          break;
        default:
          // Check for custom handlers
          const handler = messageHandlersRef.current.get(type);
          if (handler) {
            handler(data);
          }
      }
    };

    window.addEventListener('message', handleMessage);

    // Notify parent that iframe is ready (use direct postMessage initially)
    if (state.isEmbedded) {
      window.parent.postMessage({ type: 'IFRAME_READY' }, '*');
    }

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, [state.isEmbedded]);

  // Test connection when API is available
  useEffect(() => {
    if (state.api && !state.isConnected) {
      testConnection();
    }
  }, [state.api]);

  const handleInitConfig = useCallback((data: any) => {
    const newConfig: WebAIConfig = {
      apiUrl: getApiUrl(),
      tenantId: data.tenantId || 'default',
      sessionId: data.sessionId || 'default',
      useRAG: data.useRAG || false,
      ragTopK: data.ragTopK || 4,
      title: data.title || 'AI Assistant',
      debug: data.debug || false
    };

    const api = new WebAIApi(newConfig);
    
    setState(prev => ({
      ...prev,
      api,
      config: newConfig,
      isReady: true,
      error: null
    }));

    console.log('[WebAI Hook] Initialized with config:', newConfig);
  }, []);

  const handleUpdateConfig = useCallback((data: Partial<WebAIConfig>) => {
    if (state.api && state.config) {
      const newConfig = { ...state.config, ...data };
      state.api.updateConfig(newConfig);
      
      setState(prev => ({
        ...prev,
        config: newConfig
      }));

      console.log('[WebAI Hook] Config updated:', data);
    }
  }, [state.api, state.config]);

  const handleSendMessage = useCallback((data: { message: string }) => {
    // This would trigger a message send in the chat component
    // Implementation depends on how the chat component is structured
    console.log('[WebAI Hook] Send message requested:', data.message);
    
    // Dispatch custom event for chat component to listen to
    const event = new CustomEvent('webai-send-message', { detail: data });
    window.dispatchEvent(event);
  }, []);

  const handleFocusRequest = useCallback(() => {
    // Focus the chat input
    const chatInput = document.querySelector('textarea, input[type="text"]') as HTMLElement;
    if (chatInput) {
      chatInput.focus();
    }
  }, []);

  const handlePageVisible = useCallback(() => {
    // Handle when parent page becomes visible
    console.log('[WebAI Hook] Page became visible');
  }, []);

  const handleWindowResize = useCallback((data: { width: number; height: number; isMobile: boolean }) => {
    // Handle parent window resize
    console.log('[WebAI Hook] Parent window resized:', data);
    
    // Could trigger UI adjustments here
    const event = new CustomEvent('webai-window-resize', { detail: data });
    window.dispatchEvent(event);
  }, []);

  const sendToParent = useCallback((type: string, data?: any) => {
    if (state.isEmbedded && parentOriginRef.current) {
      const message = { type, data };
      window.parent.postMessage(message, parentOriginRef.current);
      console.log('[WebAI Hook] Sent to parent:', type, data);
    } else if (state.isEmbedded) {
      // Send to any origin if we don't know the parent origin yet
      const message = { type, data };
      window.parent.postMessage(message, '*');
      console.log('[WebAI Hook] Sent to parent (any origin):', type, data);
    }
  }, [state.isEmbedded]);

  const updateConfig = useCallback((newConfig: Partial<WebAIConfig>) => {
    if (state.api && state.config) {
      const updatedConfig = { ...state.config, ...newConfig };
      state.api.updateConfig(updatedConfig);
      
      setState(prev => ({
        ...prev,
        config: updatedConfig
      }));
    }
  }, [state.api, state.config]);

  const testConnection = useCallback(async (): Promise<boolean> => {
    if (!state.api) return false;

    try {
      const isConnected = await state.api.testConnection();
      setState(prev => ({
        ...prev,
        isConnected,
        error: isConnected ? null : 'Connection failed'
      }));
      return isConnected;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Connection test failed';
      setState(prev => ({
        ...prev,
        isConnected: false,
        error: errorMessage
      }));
      return false;
    }
  }, [state.api]);

  const sendMessage = useCallback((message: string) => {
    // This is a helper for programmatic message sending
    handleSendMessage({ message });
  }, [handleSendMessage]);

  const clearConversation = useCallback(async () => {
    if (state.api) {
      try {
        await state.api.clearConversationHistory();
        console.log('[WebAI Hook] Conversation cleared');
      } catch (error) {
        console.error('[WebAI Hook] Failed to clear conversation:', error);
      }
    }
  }, [state.api]);

  // Helper to get API URL
  const getApiUrl = (): string => {
    // Access environment variable in Next.js client-side
    return process.env.NEXT_PUBLIC_WEBAI_API_URL || 'https://web3ai-backend-v67-api-180395924844.us-central1.run.app';
  };

  // Add custom message handler
  const addMessageHandler = useCallback((type: string, handler: (data: any) => void) => {
    messageHandlersRef.current.set(type, handler);
  }, []);

  // Remove custom message handler
  const removeMessageHandler = useCallback((type: string) => {
    messageHandlersRef.current.delete(type);
  }, []);

  return {
    // State
    ...state,
    
    // Actions
    updateConfig,
    testConnection,
    sendMessage,
    clearConversation,
    sendToParent,

    // Extended functionality (not in interface but available)
    addMessageHandler,
    removeMessageHandler
  } as UseWebAIResult & {
    addMessageHandler: (type: string, handler: (data: any) => void) => void;
    removeMessageHandler: (type: string) => void;
  };
}

/**
 * Hook for components that need to listen to WebAI events
 */
export function useWebAIEvents() {
  const addListener = useCallback((eventType: string, handler: (event: CustomEvent) => void) => {
    window.addEventListener(eventType, handler as EventListener);
    return () => window.removeEventListener(eventType, handler as EventListener);
  }, []);

  return { addListener };
}

/**
 * Hook specifically for handling chat-related WebAI functionality
 */
export function useWebAIChat() {
  const webai = useWebAI();
  const [isStreaming, setIsStreaming] = useState(false);

  const streamChat = useCallback(async function* (messages: ChatMessage[]) {
    if (!webai.api) {
      throw new Error('WebAI API not available');
    }

    setIsStreaming(true);
    
    try {
      for await (const response of webai.api.chat(messages)) {
        yield response;
        
        if (response.finished) {
          break;
        }
      }
    } finally {
      setIsStreaming(false);
    }
  }, [webai.api]);

  const cancelStream = useCallback(() => {
    if (webai.api) {
      webai.api.cancel();
      setIsStreaming(false);
    }
  }, [webai.api]);

  return {
    ...webai,
    isStreaming,
    streamChat,
    cancelStream
  };
}