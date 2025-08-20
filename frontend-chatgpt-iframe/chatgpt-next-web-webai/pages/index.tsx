/**
 * Root page - redirects to embedded chat for iframe usage
 */

import { useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // Check if this is being loaded in an iframe or with embedded params
    const urlParams = new URLSearchParams(window.location.search);
    const isEmbedded = urlParams.get('embedded') === 'true';
    
    if (isEmbedded) {
      // Redirect to embedded chat with all parameters
      const query = Object.fromEntries(urlParams.entries());
      router.replace({
        pathname: '/embedded/chat',
        query
      });
    }
  }, [router]);

  return (
    <div className="home-page">
      <Head>
        <title>WebAI Chat</title>
        <meta name="description" content="AI Chat Assistant powered by WebAI" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      
      <div className="container">
        <h1>🤖 WebAI Chat</h1>
        <p>AI Chat Assistant powered by WebAI</p>
        
        <div className="info">
          <h2>For Embedded Usage:</h2>
          <p>This application is designed to be used as an iframe widget.</p>
          <p>Access the embedded chat at: <code>/embedded/chat?embedded=true&tenant=YOUR_TENANT&session=YOUR_SESSION&rag=true</code></p>
        </div>

        <div className="demo-link">
          <a href="/embedded/chat?embedded=true&tenant=demo&session=demo-session&rag=true">
            View Demo Chat
          </a>
        </div>
      </div>

      <style jsx>{`
        .home-page {
          min-height: 100vh;
          background: #000000;
          color: #ffffff;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .container {
          max-width: 600px;
          padding: 2rem;
          text-align: center;
        }

        h1 {
          font-size: 2.5rem;
          margin-bottom: 1rem;
          background: linear-gradient(135deg, #ffffff, #cccccc);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        p {
          font-size: 1.1rem;
          margin-bottom: 2rem;
          color: rgba(255, 255, 255, 0.8);
        }

        .info {
          background: rgba(255, 255, 255, 0.05);
          padding: 1.5rem;
          border-radius: 8px;
          margin: 2rem 0;
          text-align: left;
        }

        .info h2 {
          font-size: 1.3rem;
          margin-bottom: 1rem;
          color: #ffffff;
        }

        .info p {
          margin-bottom: 0.5rem;
          font-size: 1rem;
        }

        code {
          background: rgba(255, 255, 255, 0.1);
          padding: 0.2rem 0.4rem;
          border-radius: 4px;
          font-family: 'Monaco', 'Consolas', monospace;
          font-size: 0.9rem;
        }

        .demo-link {
          margin-top: 2rem;
        }

        .demo-link a {
          display: inline-block;
          background: linear-gradient(135deg, #007bff, #0056b3);
          color: #ffffff;
          padding: 0.75rem 1.5rem;
          border-radius: 6px;
          text-decoration: none;
          font-weight: 600;
          transition: all 0.3s ease;
        }

        .demo-link a:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
        }
      `}</style>
    </div>
  );
}