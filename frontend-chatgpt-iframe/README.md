# WebAI ChatGPT-Next-Web Iframe Integration

Complete implementation for embedding ChatGPT-Next-Web as an iframe widget with full FastAPI backend compatibility.

## Architecture

```
┌─ Website (any domain)
│  ├─ Widget Script (from Google Cloud Storage)
│  └─ Iframe Container
│     └─ ChatGPT-Next-Web App (Vercel/hosting)
│        ├─ WebAI API Adapter
│        ├─ Cross-origin Communication
│        └─ FastAPI /chat/stream Integration
```

## Features

✅ **Advanced UI** - Full ChatGPT-Next-Web capabilities (tables, diagrams, math, syntax highlighting)
✅ **Simple Embedding** - Single script tag from Google Cloud Storage
✅ **Complete Backend Compatibility** - All RAG and streaming features preserved
✅ **Cross-Origin Security** - Proper iframe communication with postMessage API
✅ **Tenant Support** - Multi-tenant authentication and configuration
✅ **Session Management** - Redis/localStorage conversation persistence
✅ **Mobile Responsive** - Adaptive sizing for all devices

## Quick Start

### 1. Deploy ChatGPT-Next-Web
```bash
cd chatgpt-next-web-webai
npm install
npm run build
vercel deploy
```

### 2. Upload Widget to Google Cloud Storage
```bash
gsutil cp widget/webai-widget-iframe.js gs://your-bucket/
gsutil web set -m index.html -e 404.html gs://your-bucket
```

### 3. Embed in Website
```html
<script>
  window.WEBAI_CHATUI_URL = "https://your-chatgpt-app.vercel.app";
  window.WEBAI_TENANT_ID = "tenant_123";
  window.WEBAI_USE_RAG = true;
</script>
<script src="https://storage.googleapis.com/your-bucket/webai-widget-iframe.js" defer></script>
```

## Directory Structure

```
frontend-chatgpt-iframe/
├── widget/                     # Google Cloud Storage widget
│   ├── webai-widget-iframe.js  # Main widget script
│   └── setup.html              # Usage example
├── chatgpt-next-web-webai/     # Modified ChatGPT-Next-Web
│   ├── lib/webai-api.ts        # FastAPI adapter
│   ├── hooks/use-webai.ts      # Integration hook
│   ├── components/             # Modified components
│   └── pages/                  # Embedded mode pages
├── deployment/                 # Deployment configs
│   ├── vercel.json             # ChatGPT-Next-Web deployment
│   ├── gcs-cors.json           # Google Cloud Storage CORS
│   └── docker/                 # Docker configurations
├── tests/                      # Testing suite
└── docs/                       # Documentation
```

## Backend Requirements

Your existing FastAPI backend is already compatible! Requires:
- `/chat/stream` endpoint with SSE streaming
- `X-Tenant-ID` header support
- ChatRequest schema with RAG parameters
- CORS configuration for iframe domains

## Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Reference](docs/configuration.md)
- [API Integration](docs/api-integration.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)