(function () {
    // Configuration (override via window before loading this script)
    const CONFIG = {
      WEBAI_API_URL: window.WEBAI_API_URL || "https://webai-chat-180395924844.us-central1.run.app",
      TENANT_ID: window.WEBAI_TENANT_ID || "your-tenant-id",
      USE_RAG: typeof window.WEBAI_USE_RAG === "boolean" ? window.WEBAI_USE_RAG : undefined,
      RAG_TOP_K: typeof window.WEBAI_RAG_TOP_K === "number" ? window.WEBAI_RAG_TOP_K : undefined,
      TITLE: window.WEBAI_TITLE || "AI Assistant"
    };
  
    // Session (persistent)
    const SESSION_ID = localStorage.getItem("webai_session_id") || (() => {
      const id = "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
      localStorage.setItem("webai_session_id", id);
      return id;
    })();
  
    // Theme
    const THEME_KEY = "webai_theme";
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initialTheme = localStorage.getItem(THEME_KEY) || (prefersDark ? "dark" : "light");
  
    // Styles
    const styles = `
      :root {
        --webai-bg: #ffffff;
        --webai-text: #111827;
        --webai-muted: #6b7280;
        --webai-card: #ffffff;
        --webai-border: #e5e7eb;
        --webai-primary: #6d28d9;
        --webai-primary-2: #4f46e5;
        --webai-primary-contrast: #ffffff;
        --webai-surface: #f7f8fa;
        --webai-shadow: 0 8px 30px rgba(0,0,0,0.12);
      }
      [data-webai-theme="dark"] {
        --webai-bg: #0b0f17;
        --webai-text: #e5e7eb;
        --webai-muted: #9ca3af;
        --webai-card: #0f172a;
        --webai-border: #1f2937;
        --webai-primary: #7c3aed;
        --webai-primary-2: #6366f1;
        --webai-primary-contrast: #ffffff;
        --webai-surface: #0b1220;
        --webai-shadow: 0 8px 30px rgba(0,0,0,0.5);
      }
  
      #webai-root {
        position: fixed;
        z-index: 999999;
        font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,system-ui,sans-serif;
      }
  
      /* Desktop sidebar */
      @media (min-width: 1024px) {
        #webai-root {
          right: 0;
          bottom: 0;
        }
        #webai-chat-widget {
          position: fixed;
          right: 20px;
          top: 20px;
          bottom: 20px;
          width: 420px;
          max-height: calc(100vh - 40px);
          transform: translateX(120%);
        }
        #webai-chat-widget.webai-open { transform: translateX(0); }
      }
  
      /* Mobile popup */
      @media (max-width: 1023px) {
        #webai-root { right: 0; bottom: 0; }
        #webai-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.45);
          opacity: 0;
          pointer-events: none;
          transition: opacity .25s ease;
        }
        #webai-overlay.webai-open { opacity: 1; pointer-events: auto; }
        #webai-chat-widget {
          position: fixed;
          left: 10px; right: 10px; bottom: 10px;
          height: 75vh; max-height: 640px;
          transform: translateY(110%);
        }
        #webai-chat-widget.webai-open { transform: translateY(0); }
      }
  
      #webai-chat-widget {
        background: var(--webai-card);
        border-radius: 14px;
        box-shadow: var(--webai-shadow);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        transition: transform .3s ease, opacity .3s ease;
        opacity: 1;
      }
  
      #webai-chat-header {
        background: linear-gradient(135deg, var(--webai-primary) 0%, var(--webai-primary-2) 100%);
        color: var(--webai-primary-contrast);
        padding: 14px 12px;
        display: flex; align-items: center; justify-content: space-between; gap: 8px;
      }
      #webai-chat-title { font-weight: 600; font-size: 16px; }
      .webai-header-actions { display: flex; gap: 6px; }
      .webai-icon-btn {
        background: rgba(255,255,255,0.15); color: #fff; border: none;
        width: 32px; height: 32px; border-radius: 8px;
        display: inline-flex; align-items: center; justify-content: center;
        cursor: pointer; transition: background .2s ease, transform .1s;
      }
      .webai-icon-btn:hover { background: rgba(255,255,255,0.25); }
      .webai-icon-btn:active { transform: scale(0.98); }
  
      #webai-chat-messages {
        flex: 1; overflow-y: auto; padding: 16px;
        background: var(--webai-surface); color: var(--webai-text);
        scroll-behavior: smooth;
      }
      .webai-message {
        display: flex; align-items: flex-start; gap: 10px;
        margin-bottom: 14px; animation: webai-fadeIn .25s ease;
      }
      @keyframes webai-fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .webai-message-avatar {
        width: 30px; height: 30px; border-radius: 50%;
        background: #e5e7eb; color: #111827; font-weight: 700;
        display: inline-flex; align-items: center; justify-content: center;
        flex-shrink: 0;
      }
      [data-webai-theme="dark"] .webai-message-avatar { background: #1f2937; color: #e5e7eb; }
      .webai-message-user .webai-message-avatar {
        background: var(--webai-primary); color: var(--webai-primary-contrast);
      }
      .webai-message-content {
        max-width: 80%;
        background: var(--webai-card);
        color: var(--webai-text);
        padding: 10px 12px; border-radius: 12px;
        border: 1px solid var(--webai-border);
        line-height: 1.5; white-space: pre-wrap;
      }
      .webai-message-user .webai-message-content {
        background: linear-gradient(135deg, var(--webai-primary) 0%, var(--webai-primary-2) 100%);
        color: var(--webai-primary-contrast); border-color: transparent;
      }
  
      #webai-chat-input-container {
        background: var(--webai-card);
        border-top: 1px solid var(--webai-border);
        padding: 10px; display: flex; gap: 8px; align-items: flex-end;
      }
      #webai-chat-input {
        flex: 1; min-height: 44px; max-height: 160px;
        padding: 10px 12px; border-radius: 10px;
        border: 1px solid var(--webai-border);
        background: var(--webai-bg); color: var(--webai-text);
        outline: none; resize: vertical; font-family: inherit; font-size: 14px;
        transition: border-color .2s ease;
      }
      #webai-chat-input:focus { border-color: var(--webai-primary); }
      #webai-send-btn {
        border: none; border-radius: 10px; padding: 10px 14px; cursor: pointer;
        background: var(--webai-primary); color: var(--webai-primary-contrast);
        display: inline-flex; align-items: center; justify-content: center; gap: 6px;
      }
  
      /* Toggle button (bottom-right) */
      #webai-chat-toggle {
        position: fixed; right: 20px; bottom: 20px;
        width: 56px; height: 56px; border-radius: 50%;
        background: linear-gradient(135deg, var(--webai-primary) 0%, var(--webai-primary-2) 100%);
        color: var(--webai-primary-contrast);
        border: none; cursor: pointer; z-index: 999998;
        box-shadow: var(--webai-shadow);
        display: inline-flex; align-items: center; justify-content: center;
        transition: transform .15s ease;
      }
      #webai-chat-toggle:hover { transform: scale(1.06); }
      #webai-chat-toggle svg { width: 26px; height: 26px; }
  
      .webai-typing-indicator {
        display: inline-flex; gap: 4px; padding: 10px 12px;
        background: var(--webai-card); border: 1px solid var(--webai-border); border-radius: 10px;
      }
      .webai-typing-dot {
        width: 8px; height: 8px; border-radius: 50%; background: var(--webai-muted);
        animation: webai-typing 1.4s infinite ease-in-out both;
      }
      .webai-typing-dot:nth-child(1){ animation-delay:-.32s }
      .webai-typing-dot:nth-child(2){ animation-delay:-.16s }
      @keyframes webai-typing { 0%,80%,100%{ transform:scale(1); opacity:1 } 40%{ transform:scale(1.3); opacity:.7 } }
  
      .webai-error-message {
        color: #ef4444; background: #fee2e2;
        border-radius: 8px; padding: 8px 10px; margin: 10px 0; font-size: 14px;
      }
      [data-webai-theme="dark"] .webai-error-message { color: #fecaca; background: #7f1d1d; }
    `;
  
    // Inject styles
    const styleEl = document.createElement("style");
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);
  
    const root = document.createElement("div");
    root.id = "webai-root";
    root.setAttribute("data-webai-theme", initialTheme);
  
    const overlay = document.createElement("div");
    overlay.id = "webai-overlay";
  
    // Widget HTML
    const widgetHTML = `
      <div id="webai-chat-widget" aria-hidden="true" aria-label="WebAI Chat">
        <div id="webai-chat-header">
          <div id="webai-chat-title">${CONFIG.TITLE}</div>
          <div class="webai-header-actions">
            <button id="webai-theme-toggle" class="webai-icon-btn" title="Toggle theme" aria-label="Toggle theme">
              <span id="webai-theme-icon">🌓</span>
            </button>
            <button id="webai-chat-close" class="webai-icon-btn" title="Close" aria-label="Close">✕</button>
          </div>
        </div>
        <div id="webai-chat-messages" role="log" aria-live="polite" aria-relevant="additions"></div>
        <div id="webai-chat-input-container">
          <textarea id="webai-chat-input" placeholder="Type your message..." rows="2"></textarea>
          <button id="webai-send-btn" title="Send" aria-label="Send">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px">
              <path d="M22 2L11 13"></path><path d="M22 2l-7 20-4-9-9-4 20-7z"></path>
            </svg>
            Send
          </button>
        </div>
      </div>
    `;
  
    // Toggle button
    const toggleHTML = `
      <button id="webai-chat-toggle" aria-haspopup="dialog" aria-expanded="false" aria-controls="webai-chat-widget" title="Open chat">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
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
    const themeBtn = document.getElementById("webai-theme-toggle");
    const messagesEl = document.getElementById("webai-chat-messages");
    const inputEl = document.getElementById("webai-chat-input");
    const sendBtn = document.getElementById("webai-send-btn");
  
    // Local conversation
    let conversation = JSON.parse(localStorage.getItem(`webai_conversation_${SESSION_ID}`) || "[]");
  
    function renderMessages() {
      messagesEl.innerHTML = "";
      conversation.forEach((msg) => {
        if (msg.role === "system") return;
        addMessageToUI(msg.content, msg.role);
      });
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
      bubble.textContent = content;
  
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
      bubble.innerHTML = '<div class="webai-typing-dot"></div><div class="webai-typing-dot"></div><div class="webai-typing-dot"></div>';
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
  
    function setTheme(next) {
      root.setAttribute("data-webai-theme", next);
      localStorage.setItem(THEME_KEY, next);
    }
  
    async function sendMessage() {
      const message = inputEl.value.trim();
      if (!message) return;
  
      addMessageToUI(message, "user");
      conversation.push({ role: "user", content: message });
      localStorage.setItem(`webai_conversation_${SESSION_ID}`, JSON.stringify(conversation));
  
      inputEl.value = "";
      showTyping();
  
      try {
        const body = { message, session_id: SESSION_ID, use_redis_conversations: false };
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
        bubble.textContent = "";
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
                bubble.textContent = fullResponse;
                messagesEl.scrollTop = messagesEl.scrollHeight;
              }
            } catch (e) {
              if (String(e?.message || "").toLowerCase().includes("error")) throw e;
            }
          }
        }
  
        conversation.push({ role: "assistant", content: fullResponse });
        localStorage.setItem(`webai_conversation_${SESSION_ID}`, JSON.stringify(conversation));
      } catch (error) {
        hideTyping();
        const errDiv = document.createElement("div");
        errDiv.className = "webai-error-message";
        errDiv.textContent = `Error: ${error.message}`;
        messagesEl.appendChild(errDiv);
        console.error("Chat error:", error);
      }
    }
  
    // Events
    document.getElementById("webai-chat-toggle").addEventListener("click", openWidget);
    document.getElementById("webai-chat-close").addEventListener("click", closeWidget);
    overlay.addEventListener("click", closeWidget);
    document.getElementById("webai-theme-toggle").addEventListener("click", () => {
      const next = root.getAttribute("data-webai-theme") === "dark" ? "light" : "dark";
      setTheme(next);
    });
    document.getElementById("webai-send-btn").addEventListener("click", sendMessage);
    document.getElementById("webai-chat-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  })();