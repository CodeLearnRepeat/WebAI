(function () {
  // Configuration (override via window before loading this script)
  const CONFIG = {
    WEBAI_API_URL: window.WEBAI_API_URL || "https://your-cloud-run-url.run.app",
    TENANT_ID: window.WEBAI_TENANT_ID || "your-tenant-id",
    USE_RAG: typeof window.WEBAI_USE_RAG === "boolean" ? window.WEBAI_USE_RAG : undefined,
    RAG_TOP_K: typeof window.WEBAI_RAG_TOP_K === "number" ? window.WEBAI_RAG_TOP_K : undefined,
    TITLE: window.WEBAI_TITLE || "AI Assistant"
  };

  // Session (per-tab) - Redis-based storage
  const SESSION_ID = sessionStorage.getItem("webai_session_id") || (() => {
    const id = "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    sessionStorage.setItem("webai_session_id", id);
    return id;
  })();

  // Widget dimensions from localStorage
  const savedDimensions = JSON.parse(localStorage.getItem("webai_dimensions") || "{}");

  // Markdown to HTML converter
  function parseMarkdown(text) {
    if (!text) return '';
    
    // Escape HTML first
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    
    // Code blocks with syntax highlighting support
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre class="webai-code-block" data-lang="${lang || ''}"><code>${code.trim()}</code></pre>`;
    });
    
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="webai-inline-code">$1</code>');
    
    // Bold
    html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    
    // Italic
    html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
    
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3 class="webai-h3">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 class="webai-h2">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 class="webai-h1">$1</h1>');
    
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="webai-link">$1</a>');
    
    // Lists
    html = html.replace(/^\* (.+)$/gim, '<li class="webai-list-item">$1</li>');
    html = html.replace(/^- (.+)$/gim, '<li class="webai-list-item">$1</li>');
    html = html.replace(/^\d+\. (.+)$/gim, '<li class="webai-list-item-numbered">$1</li>');
    
    // Wrap consecutive list items
    html = html.replace(/(<li class="webai-list-item">.*<\/li>\n?)+/g, (match) => {
      return `<ul class="webai-list">${match}</ul>`;
    });
    html = html.replace(/(<li class="webai-list-item-numbered">.*<\/li>\n?)+/g, (match) => {
      return `<ol class="webai-list-numbered">${match}</ol>`;
    });
    
    // Blockquotes
    html = html.replace(/^&gt; (.+)$/gim, '<blockquote class="webai-blockquote">$1</blockquote>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
  }

  // Ultra-modern dark theme styles
  const styles = `
    :root {
      --webai-black: #000000;
      --webai-white: #ffffff;
      --webai-gray-950: #030303;
      --webai-gray-900: #0a0a0a;
      --webai-gray-850: #0f0f0f;
      --webai-gray-800: #1a1a1a;
      --webai-gray-700: #2a2a2a;
      --webai-gray-600: #404040;
      --webai-gray-500: #666666;
      --webai-gray-400: #999999;
      --webai-gray-300: #cccccc;
      --webai-gray-200: #e5e5e5;
      --webai-gray-100: #f5f5f5;
      --webai-accent: #ffffff;
      --webai-glow: rgba(255, 255, 255, 0.1);
      --webai-shadow: 0 20px 60px rgba(0, 0, 0, 0.8), 0 0 100px rgba(0, 0, 0, 0.5);
      --webai-border-glow: 0 0 20px rgba(255, 255, 255, 0.05);
    }

    #webai-root {
      position: fixed;
      z-index: 999999;
      font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', system-ui, sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    /* Desktop resizable sidebar */
    @media (min-width: 1024px) {
      #webai-root {
        right: 0;
        bottom: 0;
      }
      #webai-chat-widget {
        position: fixed;
        right: 20px;
        top: 20px;
        width: ${savedDimensions.width || '450'}px;
        height: ${savedDimensions.height || '600'}px;
        min-width: 320px;
        min-height: 400px;
        max-width: 90vw;
        max-height: calc(100vh - 40px);
        transform: translateX(120%);
        resize: both;
        overflow: auto;
      }
      #webai-chat-widget.webai-open { 
        transform: translateX(0);
        animation: webaiSlideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      }
    }

    @keyframes webaiSlideIn {
      from { transform: translateX(120%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }

    /* Mobile popup */
    @media (max-width: 1023px) {
      #webai-root { right: 0; bottom: 0; }
      #webai-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.8);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        opacity: 0;
        pointer-events: none;
        transition: opacity .3s ease;
      }
      #webai-overlay.webai-open { opacity: 1; pointer-events: auto; }
      #webai-chat-widget {
        position: fixed;
        left: 10px; right: 10px; bottom: 10px;
        height: 85vh; max-height: 700px;
        transform: translateY(110%);
      }
      #webai-chat-widget.webai-open { 
        transform: translateY(0);
        animation: webaiSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      }
    }

    @keyframes webaiSlideUp {
      from { transform: translateY(110%); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    #webai-chat-widget {
      background: var(--webai-gray-950);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 20px;
      box-shadow: var(--webai-shadow);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transition: transform .4s cubic-bezier(0.16, 1, 0.3, 1), opacity .4s ease;
      opacity: 1;
      position: relative;
    }

    /* Resize handles */
    .webai-resize-handle {
      position: absolute;
      background: transparent;
      z-index: 10;
    }
    .webai-resize-handle:hover {
      background: rgba(255, 255, 255, 0.1);
    }
    .webai-resize-handle-h {
      width: 5px;
      top: 0;
      bottom: 0;
      cursor: ew-resize;
    }
    .webai-resize-handle-v {
      height: 5px;
      left: 0;
      right: 0;
      cursor: ns-resize;
    }
    .webai-resize-handle-left { left: 0; }
    .webai-resize-handle-top { top: 0; }
    .webai-resize-handle-corner {
      width: 15px;
      height: 15px;
      background: transparent;
      position: absolute;
      z-index: 11;
    }
    .webai-resize-handle-corner::after {
      content: '';
      position: absolute;
      bottom: 3px;
      left: 3px;
      width: 0;
      height: 0;
      border-style: solid;
      border-width: 0 0 8px 8px;
      border-color: transparent transparent rgba(255, 255, 255, 0.3) transparent;
    }
    .webai-resize-handle-nw {
      top: 0;
      left: 0;
      cursor: nw-resize;
    }

    #webai-chat-header {
      background: linear-gradient(135deg, var(--webai-gray-900) 0%, var(--webai-black) 100%);
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: var(--webai-white);
      padding: 16px 20px;
      display: flex; 
      align-items: center; 
      justify-content: space-between; 
      gap: 12px;
      flex-shrink: 0;
    }

    #webai-chat-title { 
      font-weight: 600; 
      font-size: 16px;
      letter-spacing: -0.02em;
      opacity: 0.95;
    }

    .webai-header-actions { 
      display: flex; 
      gap: 8px; 
    }

    .webai-icon-btn {
      background: rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.08);
      width: 36px; 
      height: 36px; 
      border-radius: 12px;
      display: inline-flex; 
      align-items: center; 
      justify-content: center;
      cursor: pointer; 
      transition: all .2s ease;
      font-size: 18px;
    }

    .webai-icon-btn:hover { 
      background: rgba(255, 255, 255, 0.1);
      border-color: rgba(255, 255, 255, 0.15);
      color: var(--webai-white);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .webai-icon-btn:active { 
      transform: scale(0.96); 
    }

    #webai-chat-messages {
      flex: 1; 
      overflow-y: auto; 
      padding: 20px;
      background: var(--webai-black);
      color: var(--webai-white);
      scroll-behavior: smooth;
    }

    /* Custom scrollbar */
    #webai-chat-messages::-webkit-scrollbar {
      width: 6px;
    }
    #webai-chat-messages::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.02);
    }
    #webai-chat-messages::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 3px;
    }
    #webai-chat-messages::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.15);
    }

    .webai-message {
      display: flex; 
      align-items: flex-start; 
      gap: 12px;
      margin-bottom: 20px; 
      animation: webai-fadeIn .3s ease;
    }

    @keyframes webai-fadeIn {
      from { 
        opacity: 0; 
        transform: translateY(10px); 
      }
      to { 
        opacity: 1; 
        transform: translateY(0); 
      }
    }

    .webai-message-avatar {
      width: 36px; 
      height: 36px; 
      border-radius: 12px;
      background: linear-gradient(135deg, var(--webai-gray-800), var(--webai-gray-900));
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: rgba(255, 255, 255, 0.7);
      font-weight: 600;
      font-size: 12px;
      letter-spacing: 0.5px;
      display: inline-flex; 
      align-items: center; 
      justify-content: center;
      flex-shrink: 0;
    }

    .webai-message-user .webai-message-avatar {
      background: linear-gradient(135deg, var(--webai-white), var(--webai-gray-200));
      color: var(--webai-black);
      border-color: rgba(255, 255, 255, 0.2);
    }

    .webai-message-content {
      max-width: 85%;
      background: var(--webai-gray-900);
      color: rgba(255, 255, 255, 0.9);
      padding: 14px 18px; 
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      line-height: 1.6;
      font-size: 14px;
      letter-spacing: 0.01em;
    }

    .webai-message-user .webai-message-content {
      background: linear-gradient(135deg, var(--webai-gray-800), var(--webai-gray-850));
      color: var(--webai-white);
      border-color: rgba(255, 255, 255, 0.08);
    }

    /* Markdown styles */
    .webai-message-content .webai-code-block {
      background: var(--webai-black);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      padding: 12px;
      margin: 12px 0;
      overflow-x: auto;
      font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
      font-size: 13px;
      line-height: 1.5;
    }

    .webai-message-content .webai-inline-code {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
      font-size: 0.9em;
    }

    .webai-message-content .webai-h1,
    .webai-message-content .webai-h2,
    .webai-message-content .webai-h3 {
      font-weight: 600;
      margin: 16px 0 8px 0;
      line-height: 1.3;
    }

    .webai-message-content .webai-h1 { font-size: 1.5em; }
    .webai-message-content .webai-h2 { font-size: 1.3em; }
    .webai-message-content .webai-h3 { font-size: 1.1em; }

    .webai-message-content .webai-link {
      color: rgba(255, 255, 255, 0.95);
      text-decoration: underline;
      text-decoration-color: rgba(255, 255, 255, 0.3);
      transition: text-decoration-color 0.2s ease;
    }

    .webai-message-content .webai-link:hover {
      text-decoration-color: rgba(255, 255, 255, 0.7);
    }

    .webai-message-content .webai-list,
    .webai-message-content .webai-list-numbered {
      margin: 8px 0;
      padding-left: 24px;
    }

    .webai-message-content .webai-list-item,
    .webai-message-content .webai-list-item-numbered {
      margin: 4px 0;
    }

    .webai-message-content .webai-blockquote {
      border-left: 3px solid rgba(255, 255, 255, 0.2);
      padding-left: 12px;
      margin: 8px 0;
      color: rgba(255, 255, 255, 0.7);
      font-style: italic;
    }

    #webai-chat-input-container {
      background: var(--webai-gray-950);
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding: 16px; 
      display: flex; 
      gap: 12px; 
      align-items: flex-end;
      flex-shrink: 0;
    }

    #webai-chat-input {
      flex: 1; 
      min-height: 48px; 
      max-height: 160px;
      padding: 12px 16px; 
      border-radius: 14px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: var(--webai-gray-900);
      color: var(--webai-white);
      outline: none; 
      resize: vertical; 
      font-family: inherit; 
      font-size: 14px;
      transition: all .2s ease;
      letter-spacing: 0.01em;
    }

    #webai-chat-input::placeholder {
      color: rgba(255, 255, 255, 0.3);
    }

    #webai-chat-input:focus { 
      border-color: rgba(255, 255, 255, 0.15);
      background: var(--webai-gray-850);
      box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.02);
    }

    #webai-send-btn {
      border: none; 
      border-radius: 14px; 
      padding: 12px 20px; 
      cursor: pointer;
      background: linear-gradient(135deg, var(--webai-white), var(--webai-gray-200));
      color: var(--webai-black);
      display: inline-flex; 
      align-items: center; 
      justify-content: center; 
      gap: 8px;
      font-weight: 600;
      font-size: 14px;
      letter-spacing: -0.01em;
      transition: all .2s ease;
      min-height: 48px;
    }

    #webai-send-btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px rgba(255, 255, 255, 0.15);
    }

    #webai-send-btn:active {
      transform: scale(0.98);
    }

    /* Toggle button (bottom-right) */
    #webai-chat-toggle {
      position: fixed; 
      right: 24px; 
      bottom: 24px;
      width: 60px; 
      height: 60px; 
      border-radius: 20px;
      background: linear-gradient(135deg, var(--webai-white), var(--webai-gray-200));
      color: var(--webai-black);
      border: none; 
      cursor: pointer; 
      z-index: 999998;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 80px rgba(255, 255, 255, 0.1);
      display: inline-flex; 
      align-items: center; 
      justify-content: center;
      transition: all .2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    #webai-chat-toggle:hover { 
      transform: scale(1.08) translateY(-2px);
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 0 100px rgba(255, 255, 255, 0.15);
    }

    #webai-chat-toggle svg { 
      width: 28px; 
      height: 28px; 
    }

    /* Modern loading animation - DNA helix inspired */
    .webai-typing-indicator {
      display: inline-flex; 
      align-items: center;
      justify-content: center;
      gap: 3px; 
      padding: 14px 18px;
      background: var(--webai-gray-900);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 16px;
      height: 48px;
    }

    .webai-typing-dot {
      width: 3px; 
      height: 16px; 
      background: linear-gradient(180deg, transparent, var(--webai-white), transparent);
      animation: webai-pulse 1.5s infinite ease-in-out;
      opacity: 0.8;
    }

    .webai-typing-dot:nth-child(1) { 
      animation-delay: 0s; 
      transform: rotate(0deg);
    }
    .webai-typing-dot:nth-child(2) { 
      animation-delay: 0.15s;
      transform: rotate(15deg);
    }
    .webai-typing-dot:nth-child(3) { 
      animation-delay: 0.3s;
      transform: rotate(-15deg);
    }
    .webai-typing-dot:nth-child(4) { 
      animation-delay: 0.45s;
      transform: rotate(30deg);
    }
    .webai-typing-dot:nth-child(5) { 
      animation-delay: 0.6s;
      transform: rotate(-30deg);
    }

    @keyframes webai-pulse {
      0%, 100% { 
        height: 16px;
        opacity: 0.3;
      }
      50% { 
        height: 24px;
        opacity: 1;
      }
    }

    .webai-error-message {
      color: #ff6b6b;
      background: rgba(255, 107, 107, 0.1);
      border: 1px solid rgba(255, 107, 107, 0.2);
      border-radius: 12px; 
      padding: 12px 16px; 
      margin: 12px 0; 
      font-size: 14px;
    }

    /* Smooth transitions */
    * {
      transition: background-color 0.2s ease, border-color 0.2s ease;
    }
  `;

  // Inject styles
  const styleEl = document.createElement("style");
  styleEl.textContent = styles;
  document.head.appendChild(styleEl);

  const root = document.createElement("div");
  root.id = "webai-root";

  const overlay = document.createElement("div");
  overlay.id = "webai-overlay";

  // Widget HTML with resize handles
  const widgetHTML = `
    <div id="webai-chat-widget" aria-hidden="true" aria-label="WebAI Chat">
      <div class="webai-resize-handle webai-resize-handle-h webai-resize-handle-left"></div>
      <div class="webai-resize-handle webai-resize-handle-v webai-resize-handle-top"></div>
      <div class="webai-resize-handle-corner webai-resize-handle-nw"></div>
      
      <div id="webai-chat-header">
        <div id="webai-chat-title">${CONFIG.TITLE}</div>
        <div class="webai-header-actions">
          <button id="webai-chat-minimize" class="webai-icon-btn" title="Minimize" aria-label="Minimize">−</button>
          <button id="webai-chat-close" class="webai-icon-btn" title="Close" aria-label="Close">×</button>
        </div>
      </div>
      <div id="webai-chat-messages" role="log" aria-live="polite" aria-relevant="additions"></div>
      <div id="webai-chat-input-container">
        <textarea id="webai-chat-input" placeholder="Type your message..." rows="1"></textarea>
        <button id="webai-send-btn" title="Send" aria-label="Send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:18px;height:18px">
            <path d="M22 2L11 13"></path><path d="M22 2l-7 20-4-9-9-4 20-7z"></path>
          </svg>
        </button>
      </div>
    </div>
  `;

  // Toggle button with modern icon
  const toggleHTML = `
    <button id="webai-chat-toggle" aria-haspopup="dialog" aria-expanded="false" aria-controls="webai-chat-widget" title="Open AI Assistant">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
        <path d="M2 17l10 5 10-5"></path>
        <path d="M2 12l10 5 10-5"></path>
      </svg>
    </button>
  `;

  root.innerHTML = toggleHTML + widgetHTML;
  document.body.appendChild(root);
  document.body.appendChild(overlay);

  // Elements
  const toggleBtn = document.getElementById("webai-chat-toggle");
  const widget = document.getElementById("webai-chat-widget");
  const closeBtn = document.getElementById("webai-chat-close");
  const minimizeBtn = document.getElementById("webai-chat-minimize");
  const messagesEl = document.getElementById("webai-chat-messages");
  const inputEl = document.getElementById("webai-chat-input");
  const sendBtn = document.getElementById("webai-send-btn");

  // Resize functionality
  let isResizing = false;
  let currentHandle = null;
  let startX = 0;
  let startY = 0;
  let startWidth = 0;
  let startHeight = 0;

  function initResize(e) {
    isResizing = true;
    currentHandle = e.target;
    startX = e.clientX;
    startY = e.clientY;
    startWidth = parseInt(document.defaultView.getComputedStyle(widget).width, 10);
    startHeight = parseInt(document.defaultView.getComputedStyle(widget).height, 10);
    document.addEventListener('mousemove', doResize);
    document.addEventListener('mouseup', stopResize);
    e.preventDefault();
  }

  function doResize(e) {
    if (!isResizing) return;

    if (currentHandle.classList.contains('webai-resize-handle-left')) {
      const width = startWidth - (e.clientX - startX);
      if (width > 320 && width < window.innerWidth * 0.9) {
        widget.style.width = width + 'px';
        widget.style.right = (window.innerWidth - widget.offsetLeft - width) + 'px';
      }
    } else if (currentHandle.classList.contains('webai-resize-handle-top')) {
      const height = startHeight - (e.clientY - startY);
      if (height > 400 && height < window.innerHeight - 40) {
        widget.style.height = height + 'px';
        widget.style.top = (startY + (e.clientY - startY)) + 'px';
      }
    } else if (currentHandle.classList.contains('webai-resize-handle-nw')) {
      const width = startWidth - (e.clientX - startX);
      const height = startHeight - (e.clientY - startY);
      if (width > 320 && width < window.innerWidth * 0.9) {
        widget.style.width = width + 'px';
        widget.style.right = (window.innerWidth - widget.offsetLeft - width) + 'px';
      }
      if (height > 400 && height < window.innerHeight - 40) {
        widget.style.height = height + 'px';
        widget.style.top = (startY + (e.clientY - startY)) + 'px';
      }
    }
  }

  function stopResize() {
    isResizing = false;
    document.removeEventListener('mousemove', doResize);
    document.removeEventListener('mouseup', stopResize);
    
    // Save dimensions
    const dimensions = {
      width: parseInt(widget.style.width, 10),
      height: parseInt(widget.style.height, 10)
    };
    localStorage.setItem('webai_dimensions', JSON.stringify(dimensions));
  }

  // Add resize listeners only on desktop
  if (window.innerWidth >= 1024) {
    document.querySelectorAll('.webai-resize-handle, .webai-resize-handle-corner').forEach(handle => {
      handle.addEventListener('mousedown', initResize);
    });
  }

  // Display-only messages for this session (Redis-based conversation storage)
  let displayedMessages = [];

  function renderMessages() {
    messagesEl.innerHTML = "";
    for (const msg of displayedMessages) {
      if (msg.role === "system") continue;
      addMessageToUI(msg.content, msg.role);
    }
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addMessageToUI(content, role) {
    const row = document.createElement("div");
    row.className = `webai-message webai-message-${role}`;

    const avatar = document.createElement("div");
    avatar.className = "webai-message-avatar";
    avatar.textContent = role === "user" ? "U" : "AI";

    const bubble = document.createElement("div");
    bubble.className = "webai-message-content";
    
    // Parse markdown for assistant messages
    if (role === "assistant") {
      bubble.innerHTML = parseMarkdown(content);
    } else {
      bubble.textContent = content;
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesEl.appendChild(row);
  }

  function showTyping() {
    const row = document.createElement("div");
    row.className = "webai-message webai-message-assistant";
    row.id = "webai-typing";
    const avatar = document.createElement("div");
    avatar.className = "webai-message-avatar";
    avatar.textContent = "AI";
    const bubble = document.createElement("div");
    bubble.className = "webai-typing-indicator";
    bubble.innerHTML = '<div class="webai-typing-dot"></div><div class="webai-typing-dot"></div><div class="webai-typing-dot"></div><div class="webai-typing-dot"></div><div class="webai-typing-dot"></div>';
    row.appendChild(avatar);
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById("webai-typing");
    if (el) el.remove();
  }

  function openWidget() {
    widget.classList.add("webai-open");
    toggleBtn.setAttribute("aria-expanded", "true");
    overlay.classList.add("webai-open");
    widget.setAttribute("aria-hidden", "false");
    renderMessages();
    setTimeout(() => inputEl.focus(), 50);
  }

  function closeWidget() {
    widget.classList.remove("webai-open");
    toggleBtn.setAttribute("aria-expanded", "false");
    overlay.classList.remove("webai-open");
    widget.setAttribute("aria-hidden", "true");
  }

  function minimizeWidget() {
    closeWidget();
  }

  async function sendMessage() {
    const message = inputEl.value.trim();
    if (!message) return;

    addMessageToUI(message, "user");
    displayedMessages.push({ role: "user", content: message });

    inputEl.value = "";
    inputEl.style.height = 'auto';
    showTyping();

    try {
      // Redis-based conversation storage
      const body = { message, session_id: SESSION_ID, use_redis_conversations: true };
      if (typeof CONFIG.USE_RAG !== "undefined") body.use_rag = CONFIG.USE_RAG;
      if (typeof CONFIG.RAG_TOP_K !== "undefined") body.rag_top_k = CONFIG.RAG_TOP_K;

      const response = await fetch(`${CONFIG.WEBAI_API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Tenant-ID": CONFIG.TENANT_ID },
        body: JSON.stringify(body)
      });

      if (!response.ok) {
        hideTyping();
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to get response");
      }

      hideTyping();

      const row = document.createElement("div");
      row.className = "webai-message webai-message-assistant";
      const avatar = document.createElement("div");
      avatar.className = "webai-message-avatar";
      avatar.textContent = "AI";
      const bubble = document.createElement("div");
      bubble.className = "webai-message-content";
      bubble.innerHTML = "";
      row.appendChild(avatar);
      row.appendChild(bubble);
      messagesEl.appendChild(row);

      // Robust SSE parsing with buffer
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullResponse = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx;
        while ((idx = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, idx).trimEnd();
          buffer = buffer.slice(idx + 1);
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") continue;
          try {
            const parsed = JSON.parse(payload);
            if (parsed.error) throw new Error(parsed.error);
            const delta = parsed?.choices?.[0]?.delta?.content;
            if (delta) {
              fullResponse += delta;
              // Parse markdown in real-time
              bubble.innerHTML = parseMarkdown(fullResponse);
              messagesEl.scrollTop = messagesEl.scrollHeight;
            }
          } catch (e) {
            if (String(e?.message || "").toLowerCase().includes("error")) throw e;
          }
        }
      }

      displayedMessages.push({ role: "assistant", content: fullResponse });
    } catch (error) {
      hideTyping();
      const errDiv = document.createElement("div");
      errDiv.className = "webai-error-message";
      errDiv.textContent = `Error: ${error.message}`;
      messagesEl.appendChild(errDiv);
      console.error("Chat error:", error);
    }
  }

  // Auto-resize textarea
  function autoResizeTextarea() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
  }

  // Events
  toggleBtn.addEventListener("click", openWidget);
  closeBtn.addEventListener("click", closeWidget);
  minimizeBtn.addEventListener("click", minimizeWidget);
  overlay.addEventListener("click", closeWidget);
  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("input", autoResizeTextarea);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Keyboard shortcut to open (Ctrl/Cmd + Shift + K)
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'K') {
      e.preventDefault();
      if (widget.classList.contains('webai-open')) {
        closeWidget();
      } else {
        openWidget();
      }
    }
  });
})();