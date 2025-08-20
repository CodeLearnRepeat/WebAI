/**
 * Embedded Chat Page for WebAI Integration
 *
 * This page is loaded in an iframe and provides the chat interface
 * with full integration to the WebAI FastAPI backend
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Head from 'next/head';
import { useWebAIChat, useWebAIEvents } from '@/hooks/use-webai';
import { ChatMessage } from '@/lib/webai-api';
import ChatMessages from '@/components/ChatMessages';
import ChatInput from '@/components/ChatInput';
import ChatHeader from '@/components/ChatHeader';
import LoadingSpinner from '@/components/LoadingSpinner';
import ErrorMessage from '@/components/ErrorMessage';
import { PaywallProvider, withSubscriptionProtection } from '@/components/paywall/PaywallProvider';

function EmbeddedChatContent() {
  const webai = useWebAIChat();
  const { addListener } = useWebAIEvents();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState('AI Assistant');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Listen for window resize events from parent
  useEffect(() => {
    const removeListener = addListener('webai-window-resize', (event) => {
      const { isMobile } = event.detail;
      // Adjust UI for mobile if needed
      if (chatContainerRef.current) {
        chatContainerRef.current.className = isMobile 
          ? 'chat-container mobile'
          : 'chat-container desktop';
      }
    });

    return removeListener;
  }, [addListener]);

  // Listen for programmatic message sending
  useEffect(() => {
    const removeListener = addListener('webai-send-message', (event) => {
      const { message } = event.detail;
      if (message && typeof message === 'string') {
        handleSendMessage(message);
      }
    });

    return removeListener;
  }, [addListener]);

  // Update title when config changes
  useEffect(() => {
    if (webai.config?.title) {
      setTitle(webai.config.title);
    }
  }, [webai.config]);

  // Load conversation history when WebAI is ready
  useEffect(() => {
    if (webai.isReady && webai.api && messages.length === 0) {
      loadConversationHistory();
    }
  }, [webai.isReady, webai.api]);

  const loadConversationHistory = async () => {
    if (!webai.api) return;

    try {
      const history = await webai.api.getConversationHistory();
      if (history.length > 0) {
        setMessages(history);
      }
    } catch (error) {
      console.warn('Failed to load conversation history:', error);
      // Don't show error to user for history loading failure
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!message.trim() || !webai.api || webai.isStreaming) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: message.trim(),
      id: `user-${Date.now()}`,
      timestamp: Date.now()
    };

    // Add user message
    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setError(null);
    setIsLoading(true);

    // Create assistant message placeholder
    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      id: `assistant-${Date.now()}`,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Stream the response
      const conversationMessages = [...messages, userMessage];
      
      for await (const response of webai.streamChat(conversationMessages)) {
        if (response.error) {
          throw new Error(response.error);
        }

        if (response.delta && response.content) {
          // Update the assistant message with streaming content
          setMessages(prev => 
            prev.map(msg => 
              msg.id === assistantMessage.id 
                ? { ...msg, content: msg.content + response.content }
                : msg
            )
          );
        }

        if (response.finished) {
          break;
        }
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An error occurred');
      
      // Remove the failed assistant message
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearConversation = async () => {
    try {
      if (webai.api) {
        await webai.clearConversation();
      }
      setMessages([]);
      setError(null);
      
      // Notify parent of conversation clear
      webai.sendToParent('CONVERSATION_CLEARED');
    } catch (error) {
      setError('Failed to clear conversation');
    }
  };

  const handleRetry = () => {
    if (currentMessage.trim()) {
      handleSendMessage(currentMessage);
    }
  };

  // Show loading state while WebAI initializes
  if (!webai.isReady) {
    return (
      <div className="embedded-chat loading">
        <Head>
          <title>{title}</title>
          <meta name="viewport" content="width=device-width, initial-scale=1" />
        </Head>
        <div className="loading-container">
          <LoadingSpinner />
          <p>Initializing chat...</p>
        </div>
      </div>
    );
  }

  // Show error state if connection failed
  if (webai.error && !webai.isConnected) {
    return (
      <div className="embedded-chat error">
        <Head>
          <title>Error - {title}</title>
        </Head>
        <div className="error-container">
          <ErrorMessage 
            message={webai.error} 
            onRetry={() => webai.testConnection()}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="embedded-chat" ref={chatContainerRef}>
      <Head>
        <title>{title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="AI Chat Assistant powered by WebAI" />
      </Head>

      <ChatHeader
        title={title}
        isConnected={webai.isConnected}
        ragEnabled={webai.config?.useRAG || false}
        onClear={handleClearConversation}
        onClose={() => webai.sendToParent('CLOSE_WIDGET')}
      />

      <div className="chat-body">
        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          isStreaming={webai.isStreaming}
        />
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <ErrorMessage 
          message={error} 
          onRetry={handleRetry}
          onDismiss={() => setError(null)}
        />
      )}

      <ChatInput
        value={currentMessage}
        onChange={setCurrentMessage}
        onSend={handleSendMessage}
        disabled={webai.isStreaming || !webai.isConnected}
        placeholder={
          webai.isConnected 
            ? "Type your message..." 
            : "Connecting..."
        }
      />

      <style jsx>{`
        .embedded-chat {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #000000;
          color: #ffffff;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          overflow: hidden;
        }

        .embedded-chat.loading,
        .embedded-chat.error {
          justify-content: center;
          align-items: center;
        }

        .loading-container,
        .error-container {
          text-align: center;
          padding: 2rem;
        }

        .loading-container p {
          margin-top: 1rem;
          color: rgba(255, 255, 255, 0.7);
        }

        .chat-body {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
          scroll-behavior: smooth;
        }

        .chat-body::-webkit-scrollbar {
          width: 6px;
        }

        .chat-body::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.02);
        }

        .chat-body::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 3px;
        }

        .chat-body::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.15);
        }

        .chat-container.mobile .chat-body {
          padding: 0.5rem;
        }

        @media (max-width: 768px) {
          .embedded-chat {
            font-size: 14px;
          }
          
          .chat-body {
            padding: 0.5rem;
          }
        }
      `}</style>
    </div>
  );
}

const ProtectedEmbeddedChat = withSubscriptionProtection(EmbeddedChatContent, {
  showPaywall: true,
  blockedComponent: (
    <div className="subscription-required-chat">
      <Head>
        <title>Subscription Required - WebAI Chat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      
      <div className="chat-paywall">
        <div className="paywall-content">
          <div className="paywall-icon">💬</div>
          <h2>Chat Access - Premium Feature</h2>
          <p>
            Unlimited chat conversations with your AI assistant require an active subscription.
            Subscribe for just $2/month to unlock full chat functionality.
          </p>
          
          <div className="paywall-features">
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>Unlimited conversations</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>Document processing & RAG</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>Setup workflow access</span>
            </div>
            <div className="feature-item">
              <span className="feature-icon">✅</span>
              <span>Priority support</span>
            </div>
          </div>
          
          <button
            onClick={() => {
              // Try to navigate parent window to subscription page
              if (window.parent && window.parent !== window) {
                window.parent.postMessage({ type: 'NAVIGATE_TO_SUBSCRIBE' }, '*');
              } else {
                window.location.href = '/';
              }
            }}
            className="subscribe-button"
          >
            Subscribe Now ($2/month)
          </button>
          
          <p className="paywall-note">
            Already subscribed? Please refresh this page.
          </p>
        </div>
      </div>

      <style jsx>{`
        .subscription-required-chat {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #000000;
          color: #ffffff;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .chat-paywall {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
        }

        .paywall-content {
          max-width: 400px;
          text-align: center;
        }

        .paywall-icon {
          font-size: 4rem;
          margin-bottom: 1.5rem;
          opacity: 0.8;
        }

        .paywall-content h2 {
          margin: 0 0 1rem 0;
          font-size: 1.75rem;
          font-weight: 600;
          color: #ffffff;
        }

        .paywall-content p {
          color: rgba(255, 255, 255, 0.8);
          margin: 0 0 2rem 0;
          line-height: 1.6;
        }

        .paywall-features {
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
        }

        .feature-icon {
          font-size: 1rem;
          flex-shrink: 0;
        }

        .subscribe-button {
          background: #007bff;
          color: #ffffff;
          border: none;
          padding: 1rem 2rem;
          border-radius: 8px;
          font-weight: 600;
          font-size: 1rem;
          cursor: pointer;
          transition: all 0.2s ease;
          width: 100%;
          margin-bottom: 1rem;
        }

        .subscribe-button:hover {
          background: #0056b3;
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
        }

        .paywall-note {
          font-size: 0.875rem;
          color: rgba(255, 255, 255, 0.6);
          margin: 0;
        }

        @media (max-width: 768px) {
          .chat-paywall {
            padding: 1rem;
          }

          .paywall-content {
            max-width: 100%;
          }

          .paywall-content h2 {
            font-size: 1.5rem;
          }

          .paywall-features {
            text-align: center;
          }
        }
      `}</style>
    </div>
  )
});

export default function EmbeddedChat() {
  return (
    <PaywallProvider autoCheckSubscription={true} debugMode={process.env.NODE_ENV === 'development'}>
      <ProtectedEmbeddedChat />
    </PaywallProvider>
  );
}

// Enable automatic static optimization
export const getStaticProps = async () => {
  return {
    props: {},
  };
};