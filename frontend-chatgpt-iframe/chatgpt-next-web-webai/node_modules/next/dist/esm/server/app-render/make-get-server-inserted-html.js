import React from "react";
import { isNotFoundError } from "../../client/components/not-found";
import { getURLFromRedirectError, isRedirectError } from "../../client/components/redirect";
import { getRedirectStatusCodeFromError } from "../../client/components/get-redirect-status-code-from-error";
import { renderToString } from "./render-to-string";
export function makeGetServerInsertedHTML({ polyfills, renderServerInsertedHTML }) {
    let flushedErrorMetaTagsUntilIndex = 0;
    let polyfillsFlushed = false;
    return function getServerInsertedHTML(serverCapturedErrors) {
        // Loop through all the errors that have been captured but not yet
        // flushed.
        const errorMetaTags = [];
        for(; flushedErrorMetaTagsUntilIndex < serverCapturedErrors.length; flushedErrorMetaTagsUntilIndex++){
            const error = serverCapturedErrors[flushedErrorMetaTagsUntilIndex];
            if (isNotFoundError(error)) {
                errorMetaTags.push(/*#__PURE__*/ React.createElement("meta", {
                    name: "robots",
                    content: "noindex",
                    key: error.digest
                }), process.env.NODE_ENV === "development" ? /*#__PURE__*/ React.createElement("meta", {
                    name: "next-error",
                    content: "not-found",
                    key: "next-error"
                }) : null);
            } else if (isRedirectError(error)) {
                const redirectUrl = getURLFromRedirectError(error);
                const isPermanent = getRedirectStatusCodeFromError(error) === 308 ? true : false;
                if (redirectUrl) {
                    errorMetaTags.push(/*#__PURE__*/ React.createElement("meta", {
                        httpEquiv: "refresh",
                        content: `${isPermanent ? 0 : 1};url=${redirectUrl}`,
                        key: error.digest
                    }));
                }
            }
        }
        const flushed = renderToString({
            ReactDOMServer: require("react-dom/server.edge"),
            element: /*#__PURE__*/ React.createElement(React.Fragment, null, polyfillsFlushed ? null : polyfills == null ? void 0 : polyfills.map((polyfill)=>{
                return /*#__PURE__*/ React.createElement("script", {
                    key: polyfill.src,
                    ...polyfill
                });
            }), renderServerInsertedHTML(), errorMetaTags)
        });
        polyfillsFlushed = true;
        return flushed;
    };
}

//# sourceMappingURL=make-get-server-inserted-html.js.map