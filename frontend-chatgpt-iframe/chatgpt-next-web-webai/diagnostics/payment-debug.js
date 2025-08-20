/**
 * Payment System Diagnostic Tool
 * Run this in browser console to diagnose payment issues
 */

console.log('🔍 WebAI Payment System Diagnostics');
console.log('=====================================');

// 1. Check Environment Variables
console.log('\n📋 Environment Variables:');
console.log('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY:', process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ? '✅ Set' : '❌ Missing');
console.log('NEXT_PUBLIC_WEBAI_API_URL:', process.env.NEXT_PUBLIC_WEBAI_API_URL || '❌ Missing');

// 2. Test Stripe Loading
console.log('\n🔧 Testing Stripe Loading:');
try {
  const script = document.createElement('script');
  script.src = 'https://js.stripe.com/v3/';
  script.onload = () => console.log('✅ Stripe script loaded successfully');
  script.onerror = (e) => console.error('❌ Stripe script failed to load:', e);
  document.head.appendChild(script);
} catch (e) {
  console.error('❌ Error creating Stripe script:', e);
}

// 3. Test Backend API Connectivity
console.log('\n🌐 Testing Backend API:');
const apiUrl = process.env.NEXT_PUBLIC_WEBAI_API_URL || 'https://web3ai-backend-v34-api-180395924844.us-central1.run.app';

fetch(`${apiUrl}/subscriptions/health`)
  .then(response => {
    console.log(`✅ Subscription health endpoint: ${response.status}`);
    return response.json();
  })
  .then(data => console.log('Health response:', data))
  .catch(e => console.error('❌ Subscription health check failed:', e));

fetch(`${apiUrl}/subscriptions/config`)
  .then(response => {
    console.log(`${response.ok ? '✅' : '❌'} Subscription config endpoint: ${response.status}`);
    return response.json();
  })
  .then(data => console.log('Config response:', data))
  .catch(e => console.error('❌ Subscription config failed:', e));

// 4. Check CSP Violations
console.log('\n🛡️ CSP Analysis:');
const checkCSP = () => {
  const metaCSP = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
  if (metaCSP) {
    console.log('CSP from meta tag:', metaCSP.content);
  } else {
    console.log('CSP likely set via headers (check Network tab)');
  }
  
  // Check for CSP violations in console
  console.log('Check browser console for CSP violation messages');
};
checkCSP();

// 5. Test Font Loading
console.log('\n🔤 Testing Font Loading:');
const testFont = new FontFace('TestFont', 'url(data:font/truetype;charset=utf-8;base64,ABC)');
testFont.load()
  .then(() => console.log('✅ Data URL fonts allowed'))
  .catch(e => console.error('❌ Data URL fonts blocked:', e));

// 6. Check Missing Assets
console.log('\n📁 Checking Static Assets:');
const assets = ['/favicon.ico', '/manifest.json'];
assets.forEach(asset => {
  fetch(asset)
    .then(response => console.log(`${response.ok ? '✅' : '❌'} ${asset}: ${response.status}`))
    .catch(e => console.error(`❌ ${asset} failed:`, e));
});

// 7. Local Storage Check
console.log('\n💾 Local Storage:');
console.log('Customer ID:', localStorage.getItem('webai_customer_id') || '❌ Not set');
console.log('Customer Email:', localStorage.getItem('webai_customer_email') || '❌ Not set');
console.log('Subscription Status:', localStorage.getItem('webai_subscription_status') || '❌ Not set');

console.log('\n🏁 Diagnostic complete. Check above for issues.');