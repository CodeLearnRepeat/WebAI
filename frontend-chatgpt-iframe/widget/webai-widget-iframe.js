/**
 * WebAI ChatGPT-Next-Web Iframe Widget
 * 
 * Embeddable widget that creates an iframe containing ChatGPT-Next-Web
 * with full integration to WebAI FastAPI backend.
 * 
 * Usage:
 * <script>
 *   window.WEBAI_CHATUI_URL = "https://your-chatgpt-app.vercel.app";
 *   window.WEBAI_TENANT_ID = "tenant_123";
 *   window.WEBAI_USE_RAG = true;
 *   window.WEBAI_RAG_TOP_K = 4;
 * </script>
 * <script src="https://storage.googleapis.com/your-bucket/webai-widget-iframe.js" defer></script>
 */

(function () {
  'use strict';

  // Configuration (override via window before loading this script)
  const CONFIG = {
    CHATUI_URL: window.WEBAI_CHATUI_URL || "https://webai-chatgpt.vercel.app",
    TENANT_ID: window.WEBAI_TENANT_ID || "default-tenant",
    USE_RAG: typeof window.WEBAI_USE_RAG === "boolean" ? window.WEBAI_USE_RAG : true,
    RAG_TOP_K: typeof window.WEBAI_RAG_TOP_K === "number" ? window.WEBAI_RAG_TOP_K : 4,
    TITLE: window.WEBAI_TITLE || "AI Assistant",
    DEBUG: typeof window.WEBAI_DEBUG === "boolean" ? window.WEBAI_DEBUG : false
  };

  // Generate or retrieve session ID
  const SESSION_ID = sessionStorage.getItem("webai_session_id") || (() => {
    const id = "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem("webai_session_id", id);
    return id;
  })();

  // Debug logging
  function debugLog(...args) {
    if (CONFIG.DEBUG) {
      console.log('[WebAI Widget]', ...args);
    }
  }

  debugLog('Initializing widget with config:', CONFIG);

  // Check if widget already exists
  if (document.getElementById('webai-iframe-widget')) {
    debugLog('Widget already exists, skipping initialization');
    return;
  }

  // Styles for the widget
  const styles = `
    #webai-iframe-widget {
      position: fixed;
      z-index: 999999;
      border: none;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 100px rgba(0, 0, 0, 0.2);
      background: #000;
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      opacity: 0;
      pointer-events: none;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
    }

    #webai-iframe-widget.webai-open {
      opacity: 1;
      pointer-events: auto;
    }

    #webai-iframe-widget iframe {
      width: 100%;
      height: 100%;
      border: none;
      border-radius: 16px;
      background: transparent;
    }

    #webai-toggle-btn {
      position: fixed;
      right: 24px;
      bottom: 24px;
      width: 60px;
      height: 60px;
      border-radius: 20px;
      background: linear-gradient(135deg, #ffffff, #e5e5e5);
      color: #000000;
      border: none;
      cursor: pointer;
      z-index: 999998;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 80px rgba(255, 255, 255, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    #webai-toggle-btn:hover {
      transform: scale(1.1) translateY(-2px);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 0 100px rgba(255, 255, 255, 0.15);
    }

    #webai-toggle-btn:active {
      transform: scale(1.05);
    }

    #webai-toggle-btn svg {
      width: 28px;
      height: 28px;
      transition: transform 0.3s ease;
    }

    #webai-toggle-btn.webai-open svg {
      transform: rotate(180deg);
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
      #webai-iframe-widget {
        left: 10px !important;
        right: 10px !important;
        bottom: 10px !important;
        top: 10px !important;
        width: auto !important;
        height: auto !important;
        transform: translateY(100%) !important;
      }

      #webai-iframe-widget.webai-open {
        transform: translateY(0) !important;
      }

      #webai-toggle-btn {
        right: 20px;
        bottom: 20px;
        width: 56px;
        height: 56px;
      }
    }

    /* Desktop positioning */
    @media (min-width: 769px) {
      #webai-iframe-widget {
        right: 20px;
        bottom: 20px;
        width: 420px;
        height: 650px;
        transform: translateX(110%);
      }

      #webai-iframe-widget.webai-open {
        transform: translateX(0);
      }
    }

    /* Dark mode overlay for mobile */
    #webai-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      z-index: 999997;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
    }

    #webai-overlay.webai-open {
      opacity: 1;
      pointer-events: auto;
    }

    @media (min-width: 769px) {
      #webai-overlay {
        display: none;
      }
    }
  `;

  // Inject styles
  const styleEl = document.createElement("style");
  styleEl.textContent = styles;
  document.head.appendChild(styleEl);

  // Create widget container
  const widget = document.createElement('div');
  widget.id = 'webai-iframe-widget';
  widget.setAttribute('aria-hidden', 'true');
  widget.setAttribute('aria-label', 'AI Chat Assistant');

  // Create overlay for mobile
  const overlay = document.createElement('div');
  overlay.id = 'webai-overlay';

  // Create iframe
  const iframe = document.createElement('iframe');
  iframe.setAttribute('title', CONFIG.TITLE);
  iframe.setAttribute('allow', 'clipboard-read; clipboard-write');
  iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox');

  // Build iframe URL with parameters
  const iframeUrl = new URL(CONFIG.CHATUI_URL);
  iframeUrl.searchParams.set('embedded', 'true');
  iframeUrl.searchParams.set('tenant', CONFIG.TENANT_ID);
  iframeUrl.searchParams.set('session', SESSION_ID);
  iframeUrl.searchParams.set('rag', CONFIG.USE_RAG.toString());
  iframeUrl.searchParams.set('rag_top_k', CONFIG.RAG_TOP_K.toString());
  iframeUrl.searchParams.set('title', CONFIG.TITLE);

  iframe.src = iframeUrl.toString();
  widget.appendChild(iframe);

  // Create toggle button
  const toggleBtn = document.createElement('button');
  toggleBtn.id = 'webai-toggle-btn';
  toggleBtn.setAttribute('aria-label', 'Toggle AI Assistant');
  toggleBtn.setAttribute('aria-expanded', 'false');
  toggleBtn.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
      <path d="M2 17l10 5 10-5"></path>
      <path d="M2 12l10 5 10-5"></path>
    </svg>
  `;

  // State management
  let isOpen = false;
  let isIframeReady = false;
  let pendingMessages = [];

  // Cross-origin communication
  window.addEventListener('message', (event) => {
    // Verify origin for security
    const iframeOrigin = new URL(CONFIG.CHATUI_URL).origin;
    if (event.origin !== iframeOrigin) {
      debugLog('Ignoring message from unknown origin:', event.origin);
      return;
    }

    const { type, data } = event.data;
    debugLog('Received message from iframe:', type, data);

    switch (type) {
      case 'IFRAME_READY':
        isIframeReady = true;
        debugLog('Iframe is ready');
        
        // Send pending configuration
        sendToIframe('INIT_CONFIG', {
          tenantId: CONFIG.TENANT_ID,
          sessionId: SESSION_ID,
          useRAG: CONFIG.USE_RAG,
          ragTopK: CONFIG.RAG_TOP_K,
          title: CONFIG.TITLE,
          debug: CONFIG.DEBUG
        });

        // Send any pending messages
        while (pendingMessages.length > 0) {
          const msg = pendingMessages.shift();
          iframe.contentWindow.postMessage(msg, iframeOrigin);
        }
        break;

      case 'RESIZE_WIDGET':
        if (data.width && data.height) {
          widget.style.width = data.width + 'px';
          widget.style.height = data.height + 'px';
          debugLog('Widget resized to:', data.width, 'x', data.height);
        }
        break;

      case 'CLOSE_WIDGET':
        closeWidget();
        break;

      case 'FOCUS_INPUT':
        // Handle any focus requests
        debugLog('Focus input requested');
        break;

      case 'NOTIFICATION':
        // Handle notifications from iframe
        if (data.message) {
          debugLog('Notification:', data.message);
          // Could implement desktop notifications here
        }
        break;

      case 'ERROR':
        console.error('Error from iframe:', data);
        break;

      default:
        debugLog('Unknown message type:', type);
    }
  });

  // Send message to iframe
  function sendToIframe(type, data = {}) {
    const message = { type, data };
    
    if (isIframeReady) {
      iframe.contentWindow.postMessage(message, CONFIG.CHATUI_URL);
      debugLog('Sent message to iframe:', type, data);
    } else {
      pendingMessages.push(message);
      debugLog('Queued message for iframe:', type, data);
    }
  }

  // Widget control functions
  function openWidget() {
    if (isOpen) return;
    
    isOpen = true;
    widget.classList.add('webai-open');
    overlay.classList.add('webai-open');
    toggleBtn.classList.add('webai-open');
    toggleBtn.setAttribute('aria-expanded', 'true');
    widget.setAttribute('aria-hidden', 'false');
    
    debugLog('Widget opened');
    
    // Focus iframe after animation
    setTimeout(() => {
      sendToIframe('FOCUS_REQUEST');
    }, 400);

    // Analytics/tracking
    if (window.gtag) {
      window.gtag('event', 'widget_open', {
        'custom_parameter': CONFIG.TENANT_ID
      });
    }
  }

  function closeWidget() {
    if (!isOpen) return;
    
    isOpen = false;
    widget.classList.remove('webai-open');
    overlay.classList.remove('webai-open');
    toggleBtn.classList.remove('webai-open');
    toggleBtn.setAttribute('aria-expanded', 'false');
    widget.setAttribute('aria-hidden', 'true');
    
    debugLog('Widget closed');

    // Analytics/tracking
    if (window.gtag) {
      window.gtag('event', 'widget_close', {
        'custom_parameter': CONFIG.TENANT_ID
      });
    }
  }

  function toggleWidget() {
    isOpen ? closeWidget() : openWidget();
  }

  // Event listeners
  toggleBtn.addEventListener('click', toggleWidget);
  overlay.addEventListener('click', closeWidget);

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Escape to close
    if (e.key === 'Escape' && isOpen) {
      closeWidget();
    }
    
    // Ctrl/Cmd + Shift + K to toggle
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'K') {
      e.preventDefault();
      toggleWidget();
    }
  });

  // Handle window resize
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      debugLog('Window resized, checking mobile layout');
      sendToIframe('WINDOW_RESIZE', {
        width: window.innerWidth,
        height: window.innerHeight,
        isMobile: window.innerWidth <= 768
      });
    }, 250);
  });

  // Handle page visibility changes
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      debugLog('Page hidden');
    } else {
      debugLog('Page visible');
      sendToIframe('PAGE_VISIBLE');
    }
  });

  // Add elements to page
  document.body.appendChild(overlay);
  document.body.appendChild(widget);
  document.body.appendChild(toggleBtn);

  debugLog('Widget initialized successfully');

  // Expose API for programmatic control
  window.WebAIWidget = {
    open: openWidget,
    close: closeWidget,
    toggle: toggleWidget,
    isOpen: () => isOpen,
    sendMessage: (message) => sendToIframe('SEND_MESSAGE', { message }),
    configure: (config) => sendToIframe('UPDATE_CONFIG', config)
  };

  // Auto-open widget if URL parameter is present
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('webai_open') === 'true') {
    setTimeout(openWidget, 1000);
  }

})();