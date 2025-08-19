import React from "react";
import { createServerComponentRenderer } from "./create-server-components-renderer";
import RenderResult from "../render-result";
import { renderToInitialFizzStream, createBufferedTransformStream, continueFizzStream, streamToBufferedResult, cloneTransformStream } from "../stream-utils/node-web-streams-helper";
import { canSegmentBeOverridden } from "../../client/components/match-segments";
import { stripInternalQueries } from "../internal-utils";
import { NEXT_ROUTER_PREFETCH, NEXT_ROUTER_STATE_TREE, RSC } from "../../client/components/app-router-headers";
import { createMetadataComponents } from "../../lib/metadata/metadata";
import { RequestAsyncStorageWrapper } from "../async-storage/request-async-storage-wrapper";
import { StaticGenerationAsyncStorageWrapper } from "../async-storage/static-generation-async-storage-wrapper";
import { isNotFoundError } from "../../client/components/not-found";
import { getURLFromRedirectError, isRedirectError } from "../../client/components/redirect";
import { getRedirectStatusCodeFromError } from "../../client/components/get-redirect-status-code-from-error";
import { addImplicitTags, patchFetch } from "../lib/patch-fetch";
import { AppRenderSpan } from "../lib/trace/constants";
import { getTracer } from "../lib/trace/tracer";
import { FlightRenderResult } from "./flight-render-result";
import { createErrorHandler } from "./create-error-handler";
import { getShortDynamicParamType, dynamicParamTypes } from "./get-short-dynamic-param-type";
import { getSegmentParam } from "./get-segment-param";
import { getScriptNonceFromHeader } from "./get-script-nonce-from-header";
import { parseAndValidateFlightRouterState } from "./parse-and-validate-flight-router-state";
import { validateURL } from "./validate-url";
import { createFlightRouterStateFromLoaderTree } from "./create-flight-router-state-from-loader-tree";
import { handleAction } from "./action-handler";
import { NEXT_DYNAMIC_NO_SSR_CODE } from "../../shared/lib/lazy-dynamic/no-ssr-error";
import { warn } from "../../build/output/log";
import { appendMutableCookies } from "../web/spec-extension/adapters/request-cookies";
import { createServerInsertedHTML } from "./server-inserted-html";
import { getRequiredScripts } from "./required-scripts";
import { addPathPrefix } from "../../shared/lib/router/utils/add-path-prefix";
import { makeGetServerInsertedHTML } from "./make-get-server-inserted-html";
import { walkTreeWithFlightRouterState } from "./walk-tree-with-flight-router-state";
import { createComponentTree } from "./create-component-tree";
import { getAssetQueryString } from "./get-asset-query-string";
function createNotFoundLoaderTree(loaderTree) {
    // Align the segment with parallel-route-default in next-app-loader
    return [
        "",
        {},
        loaderTree[2]
    ];
}
/* This method is important for intercepted routes to function:
 * when a route is intercepted, e.g. /blog/[slug], it will be rendered
 * with the layout of the previous page, e.g. /profile/[id]. The problem is
 * that the loader tree needs to know the dynamic param in order to render (id and slug in the example).
 * Normally they are read from the path but since we are intercepting the route, the path would not contain id,
 * so we need to read it from the router state.
 */ function findDynamicParamFromRouterState(providedFlightRouterState, segment) {
    if (!providedFlightRouterState) {
        return null;
    }
    const treeSegment = providedFlightRouterState[0];
    if (canSegmentBeOverridden(segment, treeSegment)) {
        if (!Array.isArray(treeSegment) || Array.isArray(segment)) {
            return null;
        }
        return {
            param: treeSegment[0],
            value: treeSegment[1],
            treeSegment: treeSegment,
            type: treeSegment[2]
        };
    }
    for (const parallelRouterState of Object.values(providedFlightRouterState[1])){
        const maybeDynamicParam = findDynamicParamFromRouterState(parallelRouterState, segment);
        if (maybeDynamicParam) {
            return maybeDynamicParam;
        }
    }
    return null;
}
/**
 * Returns a function that parses the dynamic segment and return the associated value.
 */ function makeGetDynamicParamFromSegment(params, providedFlightRouterState) {
    return function getDynamicParamFromSegment(// [slug] / [[slug]] / [...slug]
    segment) {
        const segmentParam = getSegmentParam(segment);
        if (!segmentParam) {
            return null;
        }
        const key = segmentParam.param;
        let value = params[key];
        // this is a special marker that will be present for interception routes
        if (value === "__NEXT_EMPTY_PARAM__") {
            value = undefined;
        }
        if (Array.isArray(value)) {
            value = value.map((i)=>encodeURIComponent(i));
        } else if (typeof value === "string") {
            value = encodeURIComponent(value);
        }
        if (!value) {
            // Handle case where optional catchall does not have a value, e.g. `/dashboard/[...slug]` when requesting `/dashboard`
            if (segmentParam.type === "optional-catchall") {
                const type = dynamicParamTypes[segmentParam.type];
                return {
                    param: key,
                    value: null,
                    type: type,
                    // This value always has to be a string.
                    treeSegment: [
                        key,
                        "",
                        type
                    ]
                };
            }
            return findDynamicParamFromRouterState(providedFlightRouterState, segment);
        }
        const type = getShortDynamicParamType(segmentParam.type);
        return {
            param: key,
            // The value that is passed to user code.
            value: value,
            // The value that is rendered in the router tree.
            treeSegment: [
                key,
                Array.isArray(value) ? value.join("/") : value,
                type
            ],
            type: type
        };
    };
}
// Handle Flight render request. This is only used when client-side navigating. E.g. when you `router.push('/dashboard')` or `router.reload()`.
async function generateFlight(ctx, options) {
    // Flight data that is going to be passed to the browser.
    // Currently a single item array but in the future multiple patches might be combined in a single request.
    let flightData = null;
    const { componentMod: { tree: loaderTree, renderToReadableStream }, getDynamicParamFromSegment, appUsingSizeAdjustment, staticGenerationStore: { urlPathname }, providedSearchParams, requestId, providedFlightRouterState } = ctx;
    if (!(options == null ? void 0 : options.skipFlight)) {
        const [MetadataTree, MetadataOutlet] = createMetadataComponents({
            tree: loaderTree,
            pathname: urlPathname,
            searchParams: providedSearchParams,
            getDynamicParamFromSegment,
            appUsingSizeAdjustment
        });
        flightData = (await walkTreeWithFlightRouterState({
            ctx,
            createSegmentPath: (child)=>child,
            loaderTreeToFilter: loaderTree,
            parentParams: {},
            flightRouterState: providedFlightRouterState,
            isFirst: true,
            // For flight, render metadata inside leaf page
            rscPayloadHead: // Adding requestId as react key to make metadata remount for each render
            /*#__PURE__*/ React.createElement(MetadataTree, {
                key: requestId
            }),
            injectedCSS: new Set(),
            injectedFontPreloadTags: new Set(),
            rootLayoutIncluded: false,
            asNotFound: ctx.isNotFoundPath || (options == null ? void 0 : options.asNotFound),
            metadataOutlet: /*#__PURE__*/ React.createElement(MetadataOutlet, null)
        })).map((path)=>path.slice(1)) // remove the '' (root) segment
        ;
    }
    const buildIdFlightDataPair = [
        ctx.renderOpts.buildId,
        flightData
    ];
    // For app dir, use the bundled version of Flight server renderer (renderToReadableStream)
    // which contains the subset React.
    const flightReadableStream = renderToReadableStream(options ? [
        options.actionResult,
        buildIdFlightDataPair
    ] : buildIdFlightDataPair, ctx.clientReferenceManifest.clientModules, {
        context: ctx.serverContexts,
        onError: ctx.flightDataRendererErrorHandler
    }).pipeThrough(createBufferedTransformStream());
    return new FlightRenderResult(flightReadableStream);
}
/**
 * A new React Component that renders the provided React Component
 * using Flight which can then be rendered to HTML.
 */ function createServerComponentsRenderer(ctx, loaderTreeToRender, preinitScripts, formState, serverComponentsRenderOpts, nonce) {
    return createServerComponentRenderer(async (props)=>{
        preinitScripts();
        // Create full component tree from root to leaf.
        const injectedCSS = new Set();
        const injectedFontPreloadTags = new Set();
        const { getDynamicParamFromSegment, query, providedSearchParams, appUsingSizeAdjustment, componentMod: { AppRouter, GlobalError }, staticGenerationStore: { urlPathname } } = ctx;
        const initialTree = createFlightRouterStateFromLoaderTree(loaderTreeToRender, getDynamicParamFromSegment, query);
        const [MetadataTree, MetadataOutlet] = createMetadataComponents({
            tree: loaderTreeToRender,
            errorType: props.asNotFound ? "not-found" : undefined,
            pathname: urlPathname,
            searchParams: providedSearchParams,
            getDynamicParamFromSegment: getDynamicParamFromSegment,
            appUsingSizeAdjustment: appUsingSizeAdjustment
        });
        const { Component: ComponentTree, styles } = await createComponentTree({
            ctx,
            createSegmentPath: (child)=>child,
            loaderTree: loaderTreeToRender,
            parentParams: {},
            firstItem: true,
            injectedCSS,
            injectedFontPreloadTags,
            rootLayoutIncluded: false,
            asNotFound: props.asNotFound,
            metadataOutlet: /*#__PURE__*/ React.createElement(MetadataOutlet, null)
        });
        return /*#__PURE__*/ React.createElement(React.Fragment, null, styles, /*#__PURE__*/ React.createElement(AppRouter, {
            buildId: ctx.renderOpts.buildId,
            assetPrefix: ctx.assetPrefix,
            initialCanonicalUrl: urlPathname,
            initialTree: initialTree,
            initialHead: /*#__PURE__*/ React.createElement(React.Fragment, null, ctx.res.statusCode > 400 && /*#__PURE__*/ React.createElement("meta", {
                name: "robots",
                content: "noindex"
            }), /*#__PURE__*/ React.createElement(MetadataTree, {
                key: ctx.requestId
            })),
            globalErrorComponent: GlobalError
        }, /*#__PURE__*/ React.createElement(ComponentTree, null)));
    }, ctx.componentMod, {
        ...serverComponentsRenderOpts,
        formState
    }, ctx.serverComponentsErrorHandler, nonce);
}
async function renderToHTMLOrFlightImpl(req, res, pagePath, query, renderOpts, baseCtx) {
    var _getTracer_getRootSpanAttributes, _staticGenerationStore_tags;
    const isFlight = req.headers[RSC.toLowerCase()] !== undefined;
    const isNotFoundPath = pagePath === "/404";
    // A unique request timestamp used by development to ensure that it's
    // consistent and won't change during this request. This is important to
    // avoid that resources can be deduped by React Float if the same resource is
    // rendered or preloaded multiple times: `<link href="a.css?v={Date.now()}"/>`.
    const requestTimestamp = Date.now();
    const { buildManifest, subresourceIntegrityManifest, serverActionsManifest, ComponentMod, dev, nextFontManifest, supportsDynamicHTML, serverActionsBodySizeLimit, buildId, appDirDevErrorLogger, assetPrefix = "" } = renderOpts;
    // We need to expose the bundled `require` API globally for
    // react-server-dom-webpack. This is a hack until we find a better way.
    if (ComponentMod.__next_app__) {
        // @ts-ignore
        globalThis.__next_require__ = ComponentMod.__next_app__.require;
        // @ts-ignore
        globalThis.__next_chunk_load__ = ComponentMod.__next_app__.loadChunk;
    }
    const extraRenderResultMeta = {};
    const appUsingSizeAdjustment = !!(nextFontManifest == null ? void 0 : nextFontManifest.appUsingSizeAdjust);
    // TODO: fix this typescript
    const clientReferenceManifest = renderOpts.clientReferenceManifest;
    const capturedErrors = [];
    const allCapturedErrors = [];
    const isNextExport = !!renderOpts.nextExport;
    const serverComponentsErrorHandler = createErrorHandler({
        _source: "serverComponentsRenderer",
        dev,
        isNextExport,
        errorLogger: appDirDevErrorLogger,
        capturedErrors
    });
    const flightDataRendererErrorHandler = createErrorHandler({
        _source: "flightDataRenderer",
        dev,
        isNextExport,
        errorLogger: appDirDevErrorLogger,
        capturedErrors
    });
    const htmlRendererErrorHandler = createErrorHandler({
        _source: "htmlRenderer",
        dev,
        isNextExport,
        errorLogger: appDirDevErrorLogger,
        capturedErrors,
        allCapturedErrors
    });
    patchFetch(ComponentMod);
    /**
   * Rules of Static & Dynamic HTML:
   *
   *    1.) We must generate static HTML unless the caller explicitly opts
   *        in to dynamic HTML support.
   *
   *    2.) If dynamic HTML support is requested, we must honor that request
   *        or throw an error. It is the sole responsibility of the caller to
   *        ensure they aren't e.g. requesting dynamic HTML for an AMP page.
   *
   * These rules help ensure that other existing features like request caching,
   * coalescing, and ISR continue working as intended.
   */ const generateStaticHTML = supportsDynamicHTML !== true;
    // Pull out the hooks/references from the component.
    const { createSearchParamsBailoutProxy, AppRouter, GlobalError, tree: loaderTree } = ComponentMod;
    const { staticGenerationStore, requestStore } = baseCtx;
    const { urlPathname } = staticGenerationStore;
    staticGenerationStore.fetchMetrics = [];
    extraRenderResultMeta.fetchMetrics = staticGenerationStore.fetchMetrics;
    // don't modify original query object
    query = {
        ...query
    };
    stripInternalQueries(query);
    const isPrefetch = req.headers[NEXT_ROUTER_PREFETCH.toLowerCase()] !== undefined;
    /**
   * Router state provided from the client-side router. Used to handle rendering from the common layout down.
   */ let providedFlightRouterState = isFlight ? parseAndValidateFlightRouterState(req.headers[NEXT_ROUTER_STATE_TREE.toLowerCase()]) : undefined;
    /**
   * The metadata items array created in next-app-loader with all relevant information
   * that we need to resolve the final metadata.
   */ let requestId;
    if (process.env.NEXT_RUNTIME === "edge") {
        requestId = crypto.randomUUID();
    } else {
        requestId = require("next/dist/compiled/nanoid").nanoid();
    }
    const isStaticGeneration = staticGenerationStore.isStaticGeneration;
    // During static generation we need to call the static generation bailout when reading searchParams
    const providedSearchParams = isStaticGeneration ? createSearchParamsBailoutProxy() : query;
    const searchParamsProps = {
        searchParams: providedSearchParams
    };
    /**
   * Server Context is specifically only available in Server Components.
   * It has to hold values that can't change while rendering from the common layout down.
   * An example of this would be that `headers` are available but `searchParams` are not because that'd mean we have to render from the root layout down on all requests.
   */ const serverContexts = [
        [
            "WORKAROUND",
            null
        ]
    ];
    /**
   * Dynamic parameters. E.g. when you visit `/dashboard/vercel` which is rendered by `/dashboard/[slug]` the value will be {"slug": "vercel"}.
   */ const params = renderOpts.params ?? {};
    const getDynamicParamFromSegment = makeGetDynamicParamFromSegment(params, providedFlightRouterState);
    const ctx = {
        ...baseCtx,
        getDynamicParamFromSegment,
        query,
        isPrefetch,
        providedSearchParams,
        requestTimestamp,
        searchParamsProps,
        appUsingSizeAdjustment,
        providedFlightRouterState,
        requestId,
        defaultRevalidate: false,
        pagePath,
        clientReferenceManifest,
        assetPrefix,
        flightDataRendererErrorHandler,
        serverComponentsErrorHandler,
        serverContexts,
        isNotFoundPath,
        res
    };
    if (isFlight && !staticGenerationStore.isStaticGeneration) {
        return generateFlight(ctx);
    }
    // Get the nonce from the incoming request if it has one.
    const csp = req.headers["content-security-policy"];
    let nonce;
    if (csp && typeof csp === "string") {
        nonce = getScriptNonceFromHeader(csp);
    }
    const serverComponentsRenderOpts = {
        inlinedDataTransformStream: new TransformStream(),
        clientReferenceManifest,
        serverContexts,
        formState: null
    };
    const validateRootLayout = dev ? {
        assetPrefix: renderOpts.assetPrefix,
        getTree: ()=>createFlightRouterStateFromLoaderTree(loaderTree, getDynamicParamFromSegment, query)
    } : undefined;
    const { HeadManagerContext } = require("../../shared/lib/head-manager-context.shared-runtime");
    // On each render, create a new `ServerInsertedHTML` context to capture
    // injected nodes from user code (`useServerInsertedHTML`).
    const { ServerInsertedHTMLProvider, renderServerInsertedHTML } = createServerInsertedHTML();
    (_getTracer_getRootSpanAttributes = getTracer().getRootSpanAttributes()) == null ? void 0 : _getTracer_getRootSpanAttributes.set("next.route", pagePath);
    const bodyResult = getTracer().wrap(AppRenderSpan.getBodyResult, {
        spanName: `render route (app) ${pagePath}`,
        attributes: {
            "next.route": pagePath
        }
    }, async ({ asNotFound, tree, formState })=>{
        const polyfills = buildManifest.polyfillFiles.filter((polyfill)=>polyfill.endsWith(".js") && !polyfill.endsWith(".module.js")).map((polyfill)=>({
                src: `${assetPrefix}/_next/${polyfill}${getAssetQueryString(ctx, false)}`,
                integrity: subresourceIntegrityManifest == null ? void 0 : subresourceIntegrityManifest[polyfill],
                crossOrigin: renderOpts.crossOrigin,
                noModule: true,
                nonce
            }));
        const [preinitScripts, bootstrapScript] = getRequiredScripts(buildManifest, assetPrefix, renderOpts.crossOrigin, subresourceIntegrityManifest, getAssetQueryString(ctx, true), nonce);
        const ServerComponentsRenderer = createServerComponentsRenderer(ctx, tree, preinitScripts, formState, serverComponentsRenderOpts, nonce);
        const content = /*#__PURE__*/ React.createElement(HeadManagerContext.Provider, {
            value: {
                appDir: true,
                nonce
            }
        }, /*#__PURE__*/ React.createElement(ServerInsertedHTMLProvider, null, /*#__PURE__*/ React.createElement(ServerComponentsRenderer, {
            asNotFound: asNotFound
        })));
        const getServerInsertedHTML = makeGetServerInsertedHTML({
            polyfills,
            renderServerInsertedHTML
        });
        try {
            const fizzStream = await renderToInitialFizzStream({
                ReactDOMServer: require("react-dom/server.edge"),
                element: content,
                streamOptions: {
                    onError: htmlRendererErrorHandler,
                    nonce,
                    // Include hydration scripts in the HTML
                    bootstrapScripts: [
                        bootstrapScript
                    ],
                    experimental_formState: formState
                }
            });
            const result = await continueFizzStream(fizzStream, {
                inlinedDataStream: serverComponentsRenderOpts.inlinedDataTransformStream.readable,
                generateStaticHTML: staticGenerationStore.isStaticGeneration || generateStaticHTML,
                getServerInsertedHTML: ()=>getServerInsertedHTML(allCapturedErrors),
                serverInsertedHTMLToHead: true,
                validateRootLayout
            });
            return result;
        } catch (err) {
            var _err_message;
            if (err.code === "NEXT_STATIC_GEN_BAILOUT" || ((_err_message = err.message) == null ? void 0 : _err_message.includes("https://nextjs.org/docs/advanced-features/static-html-export"))) {
                // Ensure that "next dev" prints the red error overlay
                throw err;
            }
            if (err.digest === NEXT_DYNAMIC_NO_SSR_CODE) {
                warn(`Entire page ${pagePath} deopted into client-side rendering. https://nextjs.org/docs/messages/deopted-into-client-rendering`, pagePath);
            }
            if (isNotFoundError(err)) {
                res.statusCode = 404;
            }
            let hasRedirectError = false;
            if (isRedirectError(err)) {
                hasRedirectError = true;
                res.statusCode = getRedirectStatusCodeFromError(err);
                if (err.mutableCookies) {
                    const headers = new Headers();
                    // If there were mutable cookies set, we need to set them on the
                    // response.
                    if (appendMutableCookies(headers, err.mutableCookies)) {
                        res.setHeader("set-cookie", Array.from(headers.values()));
                    }
                }
                const redirectUrl = addPathPrefix(getURLFromRedirectError(err), renderOpts.basePath);
                res.setHeader("Location", redirectUrl);
            }
            const is404 = res.statusCode === 404;
            // Preserve the existing RSC inline chunks from the page rendering.
            // To avoid the same stream being operated twice, clone the origin stream for error rendering.
            const serverErrorComponentsRenderOpts = {
                ...serverComponentsRenderOpts,
                inlinedDataTransformStream: cloneTransformStream(serverComponentsRenderOpts.inlinedDataTransformStream),
                formState
            };
            const errorType = is404 ? "not-found" : hasRedirectError ? "redirect" : undefined;
            const errorMeta = /*#__PURE__*/ React.createElement(React.Fragment, null, res.statusCode >= 400 && /*#__PURE__*/ React.createElement("meta", {
                name: "robots",
                content: "noindex"
            }), process.env.NODE_ENV === "development" && /*#__PURE__*/ React.createElement("meta", {
                name: "next-error",
                content: "not-found"
            }));
            const [errorPreinitScripts, errorBootstrapScript] = getRequiredScripts(buildManifest, assetPrefix, renderOpts.crossOrigin, subresourceIntegrityManifest, getAssetQueryString(ctx, false), nonce);
            const ErrorPage = createServerComponentRenderer(async ()=>{
                errorPreinitScripts();
                const [MetadataTree] = createMetadataComponents({
                    tree,
                    pathname: urlPathname,
                    errorType,
                    searchParams: providedSearchParams,
                    getDynamicParamFromSegment,
                    appUsingSizeAdjustment
                });
                const head = /*#__PURE__*/ React.createElement(React.Fragment, null, /*#__PURE__*/ React.createElement(MetadataTree, {
                    key: requestId
                }), errorMeta);
                const initialTree = createFlightRouterStateFromLoaderTree(tree, getDynamicParamFromSegment, query);
                // For metadata notFound error there's no global not found boundary on top
                // so we create a not found page with AppRouter
                return /*#__PURE__*/ React.createElement(AppRouter, {
                    buildId: buildId,
                    assetPrefix: assetPrefix,
                    initialCanonicalUrl: urlPathname,
                    initialTree: initialTree,
                    initialHead: head,
                    globalErrorComponent: GlobalError
                }, /*#__PURE__*/ React.createElement("html", {
                    id: "__next_error__"
                }, /*#__PURE__*/ React.createElement("head", null), /*#__PURE__*/ React.createElement("body", null)));
            }, ComponentMod, serverErrorComponentsRenderOpts, serverComponentsErrorHandler, nonce);
            try {
                const fizzStream = await renderToInitialFizzStream({
                    ReactDOMServer: require("react-dom/server.edge"),
                    element: /*#__PURE__*/ React.createElement(ErrorPage, null),
                    streamOptions: {
                        nonce,
                        // Include hydration scripts in the HTML
                        bootstrapScripts: [
                            errorBootstrapScript
                        ],
                        experimental_formState: formState
                    }
                });
                return await continueFizzStream(fizzStream, {
                    inlinedDataStream: serverErrorComponentsRenderOpts.inlinedDataTransformStream.readable,
                    generateStaticHTML: staticGenerationStore.isStaticGeneration,
                    getServerInsertedHTML: ()=>getServerInsertedHTML([]),
                    serverInsertedHTMLToHead: true,
                    validateRootLayout
                });
            } catch (finalErr) {
                if (process.env.NODE_ENV === "development" && isNotFoundError(finalErr)) {
                    const bailOnNotFound = require("../../client/components/dev-root-not-found-boundary").bailOnNotFound;
                    bailOnNotFound();
                }
                throw finalErr;
            }
        }
    });
    // For action requests, we handle them differently with a special render result.
    const actionRequestResult = await handleAction({
        req,
        res,
        ComponentMod,
        page: renderOpts.page,
        serverActionsManifest,
        generateFlight,
        staticGenerationStore: staticGenerationStore,
        requestStore: requestStore,
        serverActionsBodySizeLimit,
        ctx
    });
    let formState = null;
    if (actionRequestResult) {
        if (actionRequestResult.type === "not-found") {
            const notFoundLoaderTree = createNotFoundLoaderTree(loaderTree);
            return new RenderResult(await bodyResult({
                asNotFound: true,
                tree: notFoundLoaderTree,
                formState
            }), {
                ...extraRenderResultMeta
            });
        } else if (actionRequestResult.type === "done") {
            if (actionRequestResult.result) {
                actionRequestResult.result.extendMetadata(extraRenderResultMeta);
                return actionRequestResult.result;
            } else if (actionRequestResult.formState) {
                formState = actionRequestResult.formState;
            }
        }
    }
    const renderResult = new RenderResult(await bodyResult({
        asNotFound: isNotFoundPath,
        tree: loaderTree,
        formState
    }), {
        ...extraRenderResultMeta,
        waitUntil: Promise.all(staticGenerationStore.pendingRevalidates || [])
    });
    addImplicitTags(staticGenerationStore);
    extraRenderResultMeta.fetchTags = (_staticGenerationStore_tags = staticGenerationStore.tags) == null ? void 0 : _staticGenerationStore_tags.join(",");
    renderResult.extendMetadata({
        fetchTags: extraRenderResultMeta.fetchTags
    });
    if (staticGenerationStore.isStaticGeneration) {
        const htmlResult = await streamToBufferedResult(renderResult);
        // if we encountered any unexpected errors during build
        // we fail the prerendering phase and the build
        if (capturedErrors.length > 0) {
            throw capturedErrors[0];
        }
        // TODO-APP: derive this from same pass to prevent additional
        // render during static generation
        const stringifiedFlightPayload = await streamToBufferedResult(await generateFlight(ctx));
        if (staticGenerationStore.forceStatic === false) {
            staticGenerationStore.revalidate = 0;
        }
        extraRenderResultMeta.pageData = stringifiedFlightPayload;
        extraRenderResultMeta.revalidate = staticGenerationStore.revalidate ?? ctx.defaultRevalidate;
        // provide bailout info for debugging
        if (extraRenderResultMeta.revalidate === 0) {
            extraRenderResultMeta.staticBailoutInfo = {
                description: staticGenerationStore.dynamicUsageDescription,
                stack: staticGenerationStore.dynamicUsageStack
            };
        }
        return new RenderResult(htmlResult, {
            ...extraRenderResultMeta
        });
    }
    return renderResult;
}
export const renderToHTMLOrFlight = (req, res, pagePath, query, renderOpts)=>{
    const pathname = validateURL(req.url);
    return RequestAsyncStorageWrapper.wrap(renderOpts.ComponentMod.requestAsyncStorage, {
        req,
        res,
        renderOpts
    }, (requestStore)=>StaticGenerationAsyncStorageWrapper.wrap(renderOpts.ComponentMod.staticGenerationAsyncStorage, {
            urlPathname: pathname,
            renderOpts
        }, (staticGenerationStore)=>renderToHTMLOrFlightImpl(req, res, pagePath, query, renderOpts, {
                requestStore,
                staticGenerationStore,
                componentMod: renderOpts.ComponentMod,
                renderOpts
            })));
};

//# sourceMappingURL=app-render.js.map