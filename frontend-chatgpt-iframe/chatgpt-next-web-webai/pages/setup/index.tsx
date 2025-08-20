/**
 * Setup Index Page
 * Entry point for the tenant setup workflow
 */

import React, { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function SetupIndexPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the root (which is now the setup welcome page)
    router.replace('/' + window.location.search);
  }, [router]);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#000000',
      color: '#ffffff',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🚀</div>
        <h2 style={{ margin: '0 0 1rem 0' }}>Starting WebAI Setup...</h2>
        <p style={{ margin: '0', color: 'rgba(255, 255, 255, 0.7)' }}>
          Redirecting to setup wizard...
        </p>
      </div>
    </div>
  );
}