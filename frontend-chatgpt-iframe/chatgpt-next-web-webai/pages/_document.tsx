/**
 * Next.js Document component
 * Custom HTML document structure
 */

import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <meta name="description" content="AI Chat Assistant powered by WebAI" />
        <meta name="robots" content="noindex, nofollow" />
        
        {/* Preconnect to improve performance */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        
        {/* Favicon */}
        <link rel="icon" type="image/x-icon" href="/favicon.ico" />
        
        {/* Apple touch icon */}
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        
        {/* Manifest for PWA */}
        <link rel="manifest" href="/manifest.json" />
        
        {/* Open Graph tags */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content="WebAI Chat" />
        <meta property="og:description" content="AI Chat Assistant powered by WebAI" />
        <meta property="og:image" content="/og-image.png" />
        
        {/* Twitter Card tags */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="WebAI Chat" />
        <meta name="twitter:description" content="AI Chat Assistant powered by WebAI" />
        <meta name="twitter:image" content="/og-image.png" />
      </Head>
      <body>
        <Main />
        <NextScript />
        
        {/* Global script for iframe communication */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // Global postMessage handler for iframe communication
              window.addEventListener('message', function(event) {
                // Handle messages from parent window
                if (event.data && event.data.type) {
                  const { type, data } = event.data;
                  
                  // Dispatch custom events for React components to listen to
                  const customEvent = new CustomEvent('webai-' + type.toLowerCase().replace('_', '-'), {
                    detail: data
                  });
                  window.dispatchEvent(customEvent);
                }
              });
              
              // Notify parent that iframe is ready
              if (window.parent !== window) {
                window.parent.postMessage({
                  type: 'IFRAME_READY',
                  data: { url: window.location.href }
                }, '*');
              }
            `,
          }}
        />
      </body>
    </Html>
  );
}