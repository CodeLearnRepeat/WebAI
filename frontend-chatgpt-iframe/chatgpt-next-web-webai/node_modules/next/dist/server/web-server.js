"use strict";
Object.defineProperty(exports, "__esModule", {
    value: true
});
Object.defineProperty(exports, "default", {
    enumerable: true,
    get: function() {
        return NextWebServer;
    }
});
const _web = require("./api-utils/web");
const _baseserver = /*#__PURE__*/ _interop_require_wildcard(require("./base-server"));
const _etag = require("./lib/etag");
const _requestmeta = require("./request-meta");
const _web1 = /*#__PURE__*/ _interop_require_default(require("./response-cache/web"));
const _isapiroute = require("../lib/is-api-route");
const _removetrailingslash = require("../shared/lib/router/utils/remove-trailing-slash");
const _utils = require("../shared/lib/router/utils");
const _serverutils = require("./server-utils");
const _routeregex = require("../shared/lib/router/utils/route-regex");
const _incrementalcache = require("./lib/incremental-cache");
function _interop_require_default(obj) {
    return obj && obj.__esModule ? obj : {
        default: obj
    };
}
function _getRequireWildcardCache(nodeInterop) {
    if (typeof WeakMap !== "function") return null;
    var cacheBabelInterop = new WeakMap();
    var cacheNodeInterop = new WeakMap();
    return (_getRequireWildcardCache = function(nodeInterop) {
        return nodeInterop ? cacheNodeInterop : cacheBabelInterop;
    })(nodeInterop);
}
function _interop_require_wildcard(obj, nodeInterop) {
    if (!nodeInterop && obj && obj.__esModule) {
        return obj;
    }
    if (obj === null || typeof obj !== "object" && typeof obj !== "function") {
        return {
            default: obj
        };
    }
    var cache = _getRequireWildcardCache(nodeInterop);
    if (cache && cache.has(obj)) {
        return cache.get(obj);
    }
    var newObj = {};
    var hasPropertyDescriptor = Object.defineProperty && Object.getOwnPropertyDescriptor;
    for(var key in obj){
        if (key !== "default" && Object.prototype.hasOwnProperty.call(obj, key)) {
            var desc = hasPropertyDescriptor ? Object.getOwnPropertyDescriptor(obj, key) : null;
            if (desc && (desc.get || desc.set)) {
                Object.defineProperty(newObj, key, desc);
            } else {
                newObj[key] = obj[key];
            }
        }
    }
    newObj.default = obj;
    if (cache) {
        cache.set(obj, newObj);
    }
    return newObj;
}
class NextWebServer extends _baseserver.default {
    constructor(options){
        super(options);
        // Extend `renderOpts`.
        Object.assign(this.renderOpts, options.webServerConfig.extendRenderOpts);
    }
    getIncrementalCache({ requestHeaders }) {
        const dev = !!this.renderOpts.dev;
        // incremental-cache is request specific
        // although can have shared caches in module scope
        // per-cache handler
        return new _incrementalcache.IncrementalCache({
            dev,
            requestHeaders,
            requestProtocol: "https",
            appDir: this.hasAppDir,
            allowedRevalidateHeaderKeys: this.nextConfig.experimental.allowedRevalidateHeaderKeys,
            minimalMode: this.minimalMode,
            fetchCache: true,
            fetchCacheKeyPrefix: this.nextConfig.experimental.fetchCacheKeyPrefix,
            maxMemoryCacheSize: this.nextConfig.experimental.isrMemoryCacheSize,
            flushToDisk: false,
            CurCacheHandler: this.serverOptions.webServerConfig.incrementalCacheHandler,
            getPrerenderManifest: ()=>this.getPrerenderManifest()
        });
    }
    getResponseCache() {
        return new _web1.default(this.minimalMode);
    }
    async hasPage(page) {
        return page === this.serverOptions.webServerConfig.page;
    }
    getBuildId() {
        return this.serverOptions.webServerConfig.extendRenderOpts.buildId;
    }
    getHasAppDir() {
        return this.serverOptions.webServerConfig.pagesType === "app";
    }
    getPagesManifest() {
        return {
            // keep same theme but server path doesn't need to be accurate
            [this.serverOptions.webServerConfig.pathname]: `server${this.serverOptions.webServerConfig.page}.js`
        };
    }
    getAppPathsManifest() {
        const page = this.serverOptions.webServerConfig.page;
        return {
            [this.serverOptions.webServerConfig.page]: `app${page}.js`
        };
    }
    attachRequestMeta(req, parsedUrl) {
        (0, _requestmeta.addRequestMeta)(req, "__NEXT_INIT_QUERY", {
            ...parsedUrl.query
        });
    }
    getPrerenderManifest() {
        var _this_renderOpts;
        const { prerenderManifest } = this.serverOptions.webServerConfig;
        if (((_this_renderOpts = this.renderOpts) == null ? void 0 : _this_renderOpts.dev) || !prerenderManifest) {
            return {
                version: -1,
                routes: {},
                dynamicRoutes: {},
                notFoundRoutes: [],
                preview: {
                    previewModeId: "development-id"
                }
            };
        }
        return prerenderManifest;
    }
    getNextFontManifest() {
        return this.serverOptions.webServerConfig.extendRenderOpts.nextFontManifest;
    }
    async handleCatchallRenderRequest(req, res, parsedUrl) {
        let { pathname, query } = parsedUrl;
        if (!pathname) {
            throw new Error("pathname is undefined");
        }
        // interpolate query information into page for dynamic route
        // so that rewritten paths are handled properly
        const normalizedPage = this.serverOptions.webServerConfig.pathname;
        if (pathname !== normalizedPage) {
            pathname = normalizedPage;
            if ((0, _utils.isDynamicRoute)(pathname)) {
                const routeRegex = (0, _routeregex.getNamedRouteRegex)(pathname, false);
                pathname = (0, _serverutils.interpolateDynamicPath)(pathname, query, routeRegex);
                (0, _serverutils.normalizeVercelUrl)(req, true, Object.keys(routeRegex.routeKeys), true, routeRegex);
            }
        }
        // next.js core assumes page path without trailing slash
        pathname = (0, _removetrailingslash.removeTrailingSlash)(pathname);
        if (this.i18nProvider) {
            const { detectedLocale } = await this.i18nProvider.analyze(pathname);
            if (detectedLocale) {
                parsedUrl.query.__nextLocale = detectedLocale;
            }
        }
        const bubbleNoFallback = !!query._nextBubbleNoFallback;
        if ((0, _isapiroute.isAPIRoute)(pathname)) {
            delete query._nextBubbleNoFallback;
        }
        try {
            await this.render(req, res, pathname, query, parsedUrl, true);
            return {
                finished: true
            };
        } catch (err) {
            if (err instanceof _baseserver.NoFallbackError && bubbleNoFallback) {
                return {
                    finished: false
                };
            }
            throw err;
        }
    }
    renderHTML(req, res, pathname, query, renderOpts) {
        const { renderToHTML } = this.serverOptions.webServerConfig;
        if (!renderToHTML) {
            throw new Error("Invariant: routeModule should be configured when rendering pages");
        }
        // For edge runtime if the pathname hit as /_not-found entrypoint,
        // override the pathname to /404 for rendering
        if (pathname === (renderOpts.dev ? "/not-found" : "/_not-found")) {
            pathname = "/404";
        }
        return renderToHTML(req, res, pathname, query, Object.assign(renderOpts, {
            disableOptimizedLoading: true,
            runtime: "experimental-edge"
        }));
    }
    async sendRenderResult(_req, res, options) {
        res.setHeader("X-Edge-Runtime", "1");
        // Add necessary headers.
        // @TODO: Share the isomorphic logic with server/send-payload.ts.
        if (options.poweredByHeader && options.type === "html") {
            res.setHeader("X-Powered-By", "Next.js");
        }
        if (!res.getHeader("Content-Type")) {
            res.setHeader("Content-Type", options.result.contentType ? options.result.contentType : options.type === "json" ? "application/json" : "text/html; charset=utf-8");
        }
        if (options.result.isDynamic) {
            const writer = res.transformStream.writable.getWriter();
            let innerClose;
            const target = {
                write: (chunk)=>writer.write(chunk),
                end: ()=>writer.close(),
                on (_event, cb) {
                    innerClose = cb;
                },
                off (_event, _cb) {
                    innerClose = undefined;
                }
            };
            const onClose = ()=>{
                innerClose == null ? void 0 : innerClose();
            };
            // No, this cannot be replaced with `finally`, because early cancelling
            // the stream will create a rejected promise, and finally will create an
            // unhandled rejection.
            writer.closed.then(onClose, onClose);
            options.result.pipe(target);
        } else {
            const payload = await options.result.toUnchunkedString();
            res.setHeader("Content-Length", String((0, _web.byteLength)(payload)));
            if (options.generateEtags) {
                res.setHeader("ETag", (0, _etag.generateETag)(payload));
            }
            res.body(payload);
        }
        res.send();
    }
    async findPageComponents({ page, query, params }) {
        const result = await this.serverOptions.webServerConfig.loadComponent(page);
        if (!result) return null;
        return {
            query: {
                ...query || {},
                ...params || {}
            },
            components: result
        };
    }
    // Below are methods that are not implemented by the web server as they are
    // handled by the upstream proxy (edge runtime or node server).
    async runApi() {
        // This web server does not need to handle API requests.
        return true;
    }
    async handleApiRequest() {
        // Edge API requests are handled separately in minimal mode.
        return false;
    }
    loadEnvConfig() {
    // The web server does not need to load the env config. This is done by the
    // runtime already.
    }
    getPublicDir() {
        // Public files are not handled by the web server.
        return "";
    }
    getHasStaticDir() {
        return false;
    }
    async getFallback() {
        return "";
    }
    getFontManifest() {
        return undefined;
    }
    handleCompression() {
    // For the web server layer, compression is automatically handled by the
    // upstream proxy (edge runtime or node server) and we can simply skip here.
    }
    async handleUpgrade() {
    // The web server does not support web sockets.
    }
    async getFallbackErrorComponents() {
        // The web server does not need to handle fallback errors in production.
        return null;
    }
    getRoutesManifest() {
        // The web server does not need to handle rewrite rules. This is done by the
        // upstream proxy (edge runtime or node server).
        return undefined;
    }
    getMiddleware() {
        // The web server does not need to handle middleware. This is done by the
        // upstream proxy (edge runtime or node server).
        return undefined;
    }
    getFilesystemPaths() {
        return new Set();
    }
    async getPrefetchRsc() {
        return null;
    }
}

//# sourceMappingURL=web-server.js.map