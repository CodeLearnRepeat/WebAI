# WebAI ChatGPT-Next-Web Iframe Integration - Deployment Guide

This guide provides step-by-step instructions for deploying the complete iframe integration solution.

## Overview

The solution consists of two main components:
1. **Widget Script** - Hosted on Google Cloud Storage for easy embedding
2. **ChatGPT-Next-Web App** - Deployed on Vercel/hosting platform with WebAI backend integration

## Prerequisites

- Node.js 18+ installed
- Google Cloud account with Storage API enabled
- Vercel account (or alternative hosting platform)
- Your WebAI FastAPI backend running and accessible

## Part 1: Deploy ChatGPT-Next-Web Application

### Step 1: Prepare the Project

```bash
# Clone or copy the chatgpt-next-web-webai directory
cd frontend-chatgpt-iframe/chatgpt-next-web-webai

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local
```

### Step 2: Configure Environment Variables

Edit `.env.local`:

```bash
# Required: Your WebAI FastAPI backend URL
NEXT_PUBLIC_WEBAI_API_URL=https://your-webai-backend.run.app

# Optional: Enable debug mode
NEXT_PUBLIC_WEBAI_DEBUG=false

# Optional: Custom branding
NEXT_PUBLIC_APP_NAME="WebAI Chat"
```

### Step 3: Test Locally

```bash
# Start development server
npm run dev

# Test embedded mode
open http://localhost:3000/embedded/chat?embedded=true&tenant=test&session=test&rag=true
```

### Step 4: Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy (first time)
vercel --prod

# Set environment variables in Vercel dashboard or CLI
vercel env add NEXT_PUBLIC_WEBAI_API_URL production
# Enter your backend URL when prompted

# Redeploy with environment variables
vercel --prod
```

**Alternative: Deploy via Vercel Dashboard**

1. Connect your GitHub repository to Vercel
2. Set environment variables in Vercel dashboard
3. Deploy automatically on push

### Step 5: Configure Custom Domain (Optional)

```bash
# Add custom domain
vercel domains add chat.yourdomain.com

# Update DNS records as instructed by Vercel
```

## Part 2: Deploy Widget to Google Cloud Storage

### Step 1: Set up Google Cloud Storage

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Create storage bucket
gsutil mb gs://your-webai-widget-bucket

# Make bucket publicly readable
gsutil iam ch allUsers:objectViewer gs://your-webai-widget-bucket
```

### Step 2: Configure CORS

```bash
# Apply CORS configuration
gsutil cors set deployment/gcs-cors.json gs://your-webai-widget-bucket
```

### Step 3: Upload Widget Script

```bash
# Navigate to widget directory
cd frontend-chatgpt-iframe/widget

# Upload widget script
gsutil cp webai-widget-iframe.js gs://your-webai-widget-bucket/

# Set cache control (optional)
gsutil setmeta -h "Cache-Control:public, max-age=3600" gs://your-webai-widget-bucket/webai-widget-iframe.js

# Verify upload
gsutil ls gs://your-webai-widget-bucket/
```

### Step 4: Test Widget Loading

```bash
# Test direct access
curl -I https://storage.googleapis.com/your-webai-widget-bucket/webai-widget-iframe.js
```

## Part 3: Configure Your Backend

### Step 1: Update CORS Settings

Add to your FastAPI backend (`main.py`):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-chatgpt-app.vercel.app",
        "https://storage.googleapis.com",
        "https://yourdomain.com",  # Your website domains
        "*"  # For development only
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Step 2: Update Allowed Domains in Tenant Config

```python
# Update tenant configuration to allow iframe domains
tenant_config = {
    "allowed_domains": [
        "yourdomain.com",
        "*.yourdomain.com",
        "your-chatgpt-app.vercel.app"
    ],
    # ... other config
}
```

## Part 4: Integration Testing

### Step 1: Create Test HTML Page

```html
<!DOCTYPE html>
<html>
<head>
    <title>Widget Test</title>
</head>
<body>
    <h1>Test Page</h1>
    <p>This page tests the WebAI widget integration.</p>
    
    <!-- Configure widget -->
    <script>
        window.WEBAI_CHATUI_URL = "https://chatgpt-next-web-webai.vercel.app";
        window.WEBAI_TENANT_ID = "tenant_Tgyrz826g6McXjlQX173RA";
        window.WEBAI_USE_RAG = true;
        window.WEBAI_RAG_TOP_K = 4;
        window.WEBAI_TITLE = "WebAI Assistant";
        window.WEBAI_DEBUG = true;
    </script>
    
    <!-- Load widget -->
    <script src="https://storage.googleapis.com/webai_chat_widget/webai_widget/webai-widget-iframe.js" defer></script>
</body>
</html>
```

### Step 2: Test Widget Functionality

1. **Basic Loading**
   - Widget toggle button appears
   - Clicking opens iframe
   - ChatGPT-Next-Web interface loads

2. **Backend Integration**
   - Messages send successfully
   - Streaming responses work
   - RAG functionality enabled (if configured)

3. **Cross-Origin Communication**
   - Widget opens/closes properly
   - Configuration passes correctly
   - Session management works

4. **Mobile Responsiveness**
   - Test on mobile devices
   - Responsive layout works
   - Touch interactions function

### Step 3: Performance Testing

```bash
# Test widget loading speed
curl -w "@curl-format.txt" -o /dev/null -s https://storage.googleapis.com/your-webai-widget-bucket/webai-widget-iframe.js

# Test iframe loading
curl -w "@curl-format.txt" -o /dev/null -s "https://your-chatgpt-app.vercel.app/embedded/chat?embedded=true"
```

### Step 4: Production Validation

1. **Security Testing**
   - CORS configuration working
   - CSP headers properly set
   - No console errors

2. **Functionality Testing**
   - All chat features work
   - RAG integration functions
   - Session persistence works

3. **Cross-Browser Testing**
   - Chrome, Firefox, Safari
   - Mobile browsers
   - Edge cases handling

## Part 5: Monitoring and Maintenance

### Step 1: Set up Monitoring

**Vercel Analytics:**
```javascript
// Add to your Next.js app
import { Analytics } from '@vercel/analytics/react';

export default function App() {
  return (
    <>
      <Component {...pageProps} />
      <Analytics />
    </>
  );
}
```

**Google Cloud Monitoring:**
```bash
# Monitor bucket access
gcloud logging read "resource.type=gcs_bucket" --limit=50
```

### Step 2: Error Handling

Add error tracking to your widget:

```javascript
// In widget script
window.addEventListener('error', (event) => {
  if (CONFIG.DEBUG) {
    console.error('Widget error:', event.error);
  }
  
  // Optional: Send to analytics
  if (window.gtag) {
    window.gtag('event', 'exception', {
      'description': event.error.message,
      'fatal': false
    });
  }
});
```

### Step 3: Update Process

**Widget Updates:**
```bash
# Update widget script
gsutil cp webai-widget-iframe.js gs://your-webai-widget-bucket/
gsutil setmeta -h "Cache-Control:public, max-age=3600" gs://your-webai-widget-bucket/webai-widget-iframe.js
```

**App Updates:**
```bash
# Deploy updates via Vercel
vercel --prod
```

## Troubleshooting

### Common Issues

1. **Widget Not Loading**
   - Check CORS configuration
   - Verify bucket permissions
   - Check browser console for errors

2. **Iframe Not Communicating**
   - Verify postMessage origins
   - Check CSP headers
   - Ensure HTTPS on all endpoints

3. **Backend Connection Failed**
   - Verify API URL in environment
   - Check CORS on backend
   - Validate tenant ID

4. **RAG Not Working**
   - Check tenant RAG configuration
   - Verify vector store connection
   - Test RAG endpoint directly

### Debug Tools

```javascript
// Enable debug mode
window.WEBAI_DEBUG = true;

// Check widget API
console.log(window.WebAIWidget);

// Test connection
window.WebAIWidget.sendMessage("test");
```

## Security Considerations

1. **Content Security Policy**
   - Restrict iframe sources
   - Allow only necessary origins
   - Regular CSP audits

2. **API Security**
   - Validate tenant IDs
   - Rate limiting
   - Input sanitization

3. **Widget Security**
   - HTTPS only
   - Origin validation
   - Secure cross-origin communication

## Performance Optimization

1. **Widget Loading**
   - Use CDN for widget script
   - Enable compression
   - Optimize script size

2. **Iframe Performance**
   - Lazy loading
   - Resource optimization
   - Bundle size monitoring

3. **Backend Optimization**
   - Response caching
   - Connection pooling
   - Streaming optimization

This completes the comprehensive deployment guide for the WebAI ChatGPT-Next-Web iframe integration.