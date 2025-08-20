"use strict";exports.id=207,exports.ids=[207],exports.modules={1207:(e,t,n)=>{n.r(t),n.d(t,{default:()=>Document});var o=n(997),s=n(6859);function Document(){return(0,o.jsxs)(s.Html,{lang:"en",children:[(0,o.jsxs)(s.Head,{children:[o.jsx("meta",{name:"description",content:"AI Chat Assistant powered by WebAI"}),o.jsx("meta",{name:"robots",content:"noindex, nofollow"}),o.jsx("link",{rel:"preconnect",href:"https://fonts.googleapis.com"}),o.jsx("link",{rel:"preconnect",href:"https://fonts.gstatic.com",crossOrigin:"anonymous"}),o.jsx("link",{rel:"icon",type:"image/x-icon",href:"/favicon.ico"}),o.jsx("link",{rel:"apple-touch-icon",href:"/apple-touch-icon.png"}),o.jsx("link",{rel:"manifest",href:"/manifest.json"}),o.jsx("meta",{property:"og:type",content:"website"}),o.jsx("meta",{property:"og:title",content:"WebAI Chat"}),o.jsx("meta",{property:"og:description",content:"AI Chat Assistant powered by WebAI"}),o.jsx("meta",{property:"og:image",content:"/og-image.png"}),o.jsx("meta",{name:"twitter:card",content:"summary_large_image"}),o.jsx("meta",{name:"twitter:title",content:"WebAI Chat"}),o.jsx("meta",{name:"twitter:description",content:"AI Chat Assistant powered by WebAI"}),o.jsx("meta",{name:"twitter:image",content:"/og-image.png"})]}),(0,o.jsxs)("body",{children:[o.jsx(s.Main,{}),o.jsx(s.NextScript,{}),o.jsx("script",{dangerouslySetInnerHTML:{__html:`
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
            `}})]})]})}}};