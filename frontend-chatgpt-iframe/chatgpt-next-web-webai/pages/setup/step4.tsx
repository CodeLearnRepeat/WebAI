/**
 * Step 4: CMS Connection
 * Connect to WordPress, Shopify, or Webflow to sync content
 */

import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import WizardLayout, { WizardStep } from '../../components/setup/WizardLayout';

const wizardSteps: WizardStep[] = [
  { id: 1, title: 'Welcome', description: 'Introduction to setup', path: '/' },
  { id: 2, title: 'Tenant Registration', description: 'Configure your tenant settings', path: '/setup/step2' },
  { id: 3, title: 'System Capabilities', description: 'Review available features', path: '/setup/step3' },
  { id: 4, title: 'CMS Connection', description: 'Connect your website', path: '/setup/step4' },
];

type Platform = 'wordpress' | 'shopify' | 'webflow';

interface SyncStatus {
  status: 'idle' | 'testing' | 'syncing' | 'success' | 'error';
  message?: string;
  details?: any;
}

export default function CMSConnectionPage() {
  const router = useRouter();
  const [platform, setPlatform] = useState<Platform>('wordpress');
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({ status: 'idle' });

  // WordPress state
  const [wpSiteUrl, setWpSiteUrl] = useState('');
  const [wpUsername, setWpUsername] = useState('');
  const [wpPassword, setWpPassword] = useState('');
  const [wpIncludePosts, setWpIncludePosts] = useState(true);
  const [wpIncludePages, setWpIncludePages] = useState(true);

  // Shopify state
  const [shopifyDomain, setShopifyDomain] = useState('');
  const [shopifyToken, setShopifyToken] = useState('');
  const [shopifyIncludeProducts, setShopifyIncludeProducts] = useState(true);
  const [shopifyIncludePages, setShopifyIncludePages] = useState(true);

  // Webflow state
  const [webflowSiteId, setWebflowSiteId] = useState('');
  const [webflowToken, setWebflowToken] = useState('');
  const [webflowDomain, setWebflowDomain] = useState('');

  const handleTestConnection = async () => {
    setSyncStatus({ status: 'testing', message: 'Testing connection...' });

    try {
      const apiUrl = process.env.NEXT_PUBLIC_WEBAI_API_URL;
      const storedTenantId = localStorage.getItem('webai_tenant_id');

      let endpoint = '';
      let credentials: any = {};

      if (platform === 'wordpress') {
        endpoint = `${apiUrl}/cms/wordpress/test`;
        credentials = {
          site_url: wpSiteUrl,
          username: wpUsername || null,
          app_password: wpPassword || null,
          include_posts: wpIncludePosts,
          include_pages: wpIncludePages
        };
      } else if (platform === 'shopify') {
        endpoint = `${apiUrl}/cms/shopify/test`;
        credentials = {
          shop_domain: shopifyDomain,
          access_token: shopifyToken,
          include_products: shopifyIncludeProducts,
          include_pages: shopifyIncludePages
        };
      } else if (platform === 'webflow') {
        endpoint = `${apiUrl}/cms/webflow/test`;
        credentials = {
          site_id: webflowSiteId,
          api_token: webflowToken,
          site_domain: webflowDomain
        };
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': storedTenantId || 'setup'
        },
        body: JSON.stringify(credentials)
      });

      const result = await response.json();

      if (result.status === 'success') {
        setSyncStatus({
          status: 'success',
          message: 'Connection successful!',
          details: result
        });
      } else {
        setSyncStatus({
          status: 'error',
          message: result.message || 'Connection failed'
        });
      }
    } catch (error: any) {
      setSyncStatus({
        status: 'error',
        message: error.message || 'Failed to test connection'
      });
    }
  };

  const handleSyncContent = async () => {
    setSyncStatus({ status: 'syncing', message: 'Syncing content...' });

    try {
      const apiUrl = process.env.NEXT_PUBLIC_WEBAI_API_URL;
      const storedTenantId = localStorage.getItem('webai_tenant_id');

      let endpoint = '';
      let credentials: any = {};

      if (platform === 'wordpress') {
        endpoint = `${apiUrl}/cms/wordpress/sync`;
        credentials = {
          site_url: wpSiteUrl,
          username: wpUsername || null,
          app_password: wpPassword || null,
          include_posts: wpIncludePosts,
          include_pages: wpIncludePages
        };
      } else if (platform === 'shopify') {
        endpoint = `${apiUrl}/cms/shopify/sync`;
        credentials = {
          shop_domain: shopifyDomain,
          access_token: shopifyToken,
          include_products: shopifyIncludeProducts,
          include_pages: shopifyIncludePages
        };
      } else if (platform === 'webflow') {
        endpoint = `${apiUrl}/cms/webflow/sync`;
        credentials = {
          site_id: webflowSiteId,
          api_token: webflowToken,
          site_domain: webflowDomain
        };
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': storedTenantId || 'setup'
        },
        body: JSON.stringify(credentials)
      });

      const result = await response.json();

      if (response.ok && result.status === 'success') {
        setSyncStatus({
          status: 'success',
          message: `Successfully synced ${result.items_synced} items (${result.chunks_created} chunks, ${result.embeddings_generated} embeddings)`,
          details: result
        });
      } else {
        setSyncStatus({
          status: 'error',
          message: result.detail || result.message || 'Sync failed'
        });
      }
    } catch (error: any) {
      setSyncStatus({
        status: 'error',
        message: error.message || 'Failed to sync content'
      });
    }
  };

  const handleNext = () => {
    router.push('/embedded/chat' + window.location.search);
  };

  const handlePrevious = () => {
    router.push('/setup/step3' + window.location.search);
  };

  const handleCancel = () => {
    router.push('/embedded/chat' + window.location.search);
  };

  const isFormValid = () => {
    if (platform === 'wordpress') {
      return wpSiteUrl.trim() !== '';
    } else if (platform === 'shopify') {
      return shopifyDomain.trim() !== '' && shopifyToken.trim() !== '';
    } else if (platform === 'webflow') {
      return webflowSiteId.trim() !== '' && webflowToken.trim() !== '' && webflowDomain.trim() !== '';
    }
    return false;
  };

  return (
    <>
      <Head>
        <title>CMS Connection - WebAI Setup</title>
      </Head>

      <WizardLayout
        currentStep={4}
        steps={wizardSteps}
        onNext={handleNext}
        onPrevious={handlePrevious}
        onCancel={handleCancel}
        nextLabel="Complete Setup"
      >
        <div className="cms-connection-page">
          <h2>Connect Your Website</h2>
          <p className="description">
            Sync your website content to enable intelligent chat responses based on your actual data.
          </p>

          {/* Platform Selection */}
          <div className="form-group">
            <label>Select Your Platform</label>
            <div className="platform-selector">
              <button
                className={`platform-btn ${platform === 'wordpress' ? 'active' : ''}`}
                onClick={() => setPlatform('wordpress')}
              >
                <span className="platform-icon">📝</span>
                WordPress
              </button>
              <button
                className={`platform-btn ${platform === 'shopify' ? 'active' : ''}`}
                onClick={() => setPlatform('shopify')}
              >
                <span className="platform-icon">🛍️</span>
                Shopify
              </button>
              <button
                className={`platform-btn ${platform === 'webflow' ? 'active' : ''}`}
                onClick={() => setPlatform('webflow')}
              >
                <span className="platform-icon">🌊</span>
                Webflow
              </button>
            </div>
          </div>

          {/* WordPress Form */}
          {platform === 'wordpress' && (
            <div className="platform-form">
              <h3>WordPress Connection</h3>
              <div className="form-group">
                <label>WordPress Site URL *</label>
                <input
                  type="url"
                  placeholder="https://your-site.com"
                  value={wpSiteUrl}
                  onChange={(e) => setWpSiteUrl(e.target.value)}
                />
                <small>The full URL to your WordPress site</small>
              </div>
              <div className="form-group">
                <label>Username (Optional)</label>
                <input
                  type="text"
                  placeholder="admin"
                  value={wpUsername}
                  onChange={(e) => setWpUsername(e.target.value)}
                />
                <small>For private content access</small>
              </div>
              <div className="form-group">
                <label>Application Password (Optional)</label>
                <input
                  type="password"
                  placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                  value={wpPassword}
                  onChange={(e) => setWpPassword(e.target.value)}
                />
                <small>
                  Generate at: Settings → Application Passwords. <a href="https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/" target="_blank" rel="noopener">Learn more</a>
                </small>
              </div>
              <div className="form-group-inline">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={wpIncludePosts}
                    onChange={(e) => setWpIncludePosts(e.target.checked)}
                  />
                  Include Posts
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={wpIncludePages}
                    onChange={(e) => setWpIncludePages(e.target.checked)}
                  />
                  Include Pages
                </label>
              </div>
            </div>
          )}

          {/* Shopify Form */}
          {platform === 'shopify' && (
            <div className="platform-form">
              <h3>Shopify Connection</h3>
              <div className="form-group">
                <label>Shop Domain *</label>
                <input
                  type="text"
                  placeholder="mystore.myshopify.com"
                  value={shopifyDomain}
                  onChange={(e) => setShopifyDomain(e.target.value)}
                />
                <small>Your Shopify store domain</small>
              </div>
              <div className="form-group">
                <label>Admin API Access Token *</label>
                <input
                  type="password"
                  placeholder="shpat_..."
                  value={shopifyToken}
                  onChange={(e) => setShopifyToken(e.target.value)}
                />
                <small>
                  Create at: Apps → Develop apps → Create an app. <a href="https://shopify.dev/docs/apps/auth/admin-app-access-tokens" target="_blank" rel="noopener">Learn more</a>
                </small>
              </div>
              <div className="form-group-inline">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={shopifyIncludeProducts}
                    onChange={(e) => setShopifyIncludeProducts(e.target.checked)}
                  />
                  Include Products
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={shopifyIncludePages}
                    onChange={(e) => setShopifyIncludePages(e.target.checked)}
                  />
                  Include Pages
                </label>
              </div>
            </div>
          )}

          {/* Webflow Form */}
          {platform === 'webflow' && (
            <div className="platform-form">
              <h3>Webflow Connection</h3>
              <div className="form-group">
                <label>Site ID *</label>
                <input
                  type="text"
                  placeholder="5f7..."
                  value={webflowSiteId}
                  onChange={(e) => setWebflowSiteId(e.target.value)}
                />
                <small>Find in Site Settings → General</small>
              </div>
              <div className="form-group">
                <label>API Token *</label>
                <input
                  type="password"
                  placeholder="..."
                  value={webflowToken}
                  onChange={(e) => setWebflowToken(e.target.value)}
                />
                <small>
                  Generate at: Account Settings → Integrations → API Access. <a href="https://developers.webflow.com/docs/getting-started-with-apps" target="_blank" rel="noopener">Learn more</a>
                </small>
              </div>
              <div className="form-group">
                <label>Site Domain *</label>
                <input
                  type="text"
                  placeholder="your-site.webflow.io"
                  value={webflowDomain}
                  onChange={(e) => setWebflowDomain(e.target.value)}
                />
                <small>Your published site domain</small>
              </div>
            </div>
          )}

          {/* Status Message */}
          {syncStatus.status !== 'idle' && (
            <div className={`status-message status-${syncStatus.status}`}>
              {syncStatus.status === 'testing' && '⏳ '}
              {syncStatus.status === 'syncing' && '🔄 '}
              {syncStatus.status === 'success' && '✅ '}
              {syncStatus.status === 'error' && '❌ '}
              {syncStatus.message}
              {syncStatus.details && syncStatus.status === 'success' && (
                <div className="status-details">
                  {syncStatus.details.site_name && <div>Site: {syncStatus.details.site_name}</div>}
                  {syncStatus.details.shop_name && <div>Shop: {syncStatus.details.shop_name}</div>}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="action-buttons">
            <button
              onClick={handleTestConnection}
              disabled={!isFormValid() || syncStatus.status === 'testing' || syncStatus.status === 'syncing'}
              className="secondary-btn"
            >
              Test Connection
            </button>
            <button
              onClick={handleSyncContent}
              disabled={!isFormValid() || syncStatus.status === 'testing' || syncStatus.status === 'syncing'}
              className="primary-btn"
            >
              {syncStatus.status === 'syncing' ? 'Syncing...' : 'Sync Content'}
            </button>
          </div>

          <div className="info-box">
            <strong>💡 Tip:</strong> You can skip this step and sync your content later. The chatbot will work without synced content, but won't have knowledge of your specific website.
          </div>
        </div>

        <style jsx>{`
          .cms-connection-page {
            max-width: 700px;
            margin: 0 auto;
          }

          h2 {
            margin: 0 0 1rem 0;
            color: #ffffff;
          }

          .description {
            color: rgba(255, 255, 255, 0.7);
            margin-bottom: 2rem;
          }

          .form-group {
            margin-bottom: 1.5rem;
          }

          label {
            display: block;
            margin-bottom: 0.5rem;
            color: #ffffff;
            font-weight: 500;
          }

          input[type="text"],
          input[type="url"],
          input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
            font-size: 1rem;
          }

          input[type="text"]:focus,
          input[type="url"]:focus,
          input[type="password"]:focus {
            outline: none;
            border-color: #007bff;
            background: rgba(255, 255, 255, 0.1);
          }

          small {
            display: block;
            margin-top: 0.25rem;
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.875rem;
          }

          small a {
            color: #93c5fd;
            text-decoration: none;
          }

          small a:hover {
            text-decoration: underline;
          }

          .platform-selector {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
          }

          .platform-btn {
            padding: 1rem;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            color: rgba(255, 255, 255, 0.7);
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
          }

          .platform-btn:hover {
            border-color: rgba(255, 255, 255, 0.4);
            background: rgba(255, 255, 255, 0.1);
          }

          .platform-btn.active {
            border-color: #007bff;
            background: rgba(0, 123, 255, 0.2);
            color: #ffffff;
          }

          .platform-icon {
            font-size: 2rem;
          }

          .platform-form {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
          }

          .platform-form h3 {
            margin: 0 0 1.5rem 0;
            color: #ffffff;
          }

          .form-group-inline {
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
          }

          .checkbox-label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
          }

          input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
          }

          .status-message {
            padding: 1rem;
            border-radius: 8px;
            margin: 1.5rem 0;
          }

          .status-testing,
          .status-syncing {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.3);
            color: #ffc107;
          }

          .status-success {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.3);
            color: #4caf50;
          }

          .status-error {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.3);
            color: #f44336;
          }

          .status-details {
            margin-top: 0.5rem;
            font-size: 0.9rem;
            opacity: 0.9;
          }

          .action-buttons {
            display: flex;
            gap: 1rem;
            margin: 2rem 0;
          }

          .primary-btn,
          .secondary-btn {
            flex: 1;
            padding: 0.875rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
          }

          .primary-btn {
            background: #007bff;
            color: #ffffff;
          }

          .primary-btn:hover:not(:disabled) {
            background: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
          }

          .secondary-btn {
            background: transparent;
            color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.3);
          }

          .secondary-btn:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border-color: rgba(255, 255, 255, 0.5);
          }

          .primary-btn:disabled,
          .secondary-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }

          .info-box {
            background: rgba(0, 123, 255, 0.1);
            border: 1px solid rgba(0, 123, 255, 0.2);
            border-radius: 8px;
            padding: 1rem;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
          }

          @media (max-width: 768px) {
            .platform-selector {
              grid-template-columns: 1fr;
            }

            .form-group-inline {
              flex-direction: column;
              gap: 1rem;
            }

            .action-buttons {
              flex-direction: column;
            }
          }
        `}</style>
      </WizardLayout>
    </>
  );
}