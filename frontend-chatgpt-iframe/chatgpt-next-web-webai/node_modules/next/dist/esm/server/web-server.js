import { byteLength } from "./api-utils/web";
import BaseServer, { NoFallbackError } from "./base-server";
import { generateETag } from "./lib/etag";
import { addRequestMeta } from "./request-meta";
import WebResponseCache from "./response-cache/web";
import { isAPIRoute } from "../lib/is-api-route";
import { removeTrailingSlash } from "../shared/lib/router/utils/remove-trailing-slash";
import { isDynamicRoute } from "../shared/lib/router/utils";
import { interpolateDynamicPath, normalizeVercelUrl } from "./server-utils";
import { getNamedRouteRegex } from "../shared/lib/router/utils/route-regex";
import { IncrementalCache } from "./lib/incremental-cache";
export default class NextWebServer extends BaseServer {
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
        return new IncrementalCache({
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
        return new WebResponseCache(this.minimalMode);
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
        addRequestMeta(req, "__NEXT_INIT_QUERY", {
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
            if (isDynamicRoute(pathname)) {
                const routeRegex = getNamedRouteRegex(pathname, false);
                pathname = interpolateDynamicPath(pathname, query, routeRegex);
                normalizeVercelUrl(req, true, Object.keys(routeRegex.routeKeys), true, routeRegex);
            }
        }
        // next.js core assumes page path without trailing slash
        pathname = removeTrailingSlash(pathname);
        if (this.i18nProvider) {
            const { detectedLocale } = await this.i18nProvider.analyze(pathname);
            if (detectedLocale) {
                parsedUrl.query.__nextLocale = detectedLocale;
            }
        }
        const bubbleNoFallback = !!query._nextBubbleNoFallback;
        if (isAPIRoute(pathname)) {
            delete query._nextBubbleNoFallback;
        }
        try {
            await this.render(req, res, pathname, query, parsedUrl, true);
            return {
                finished: true
            };
        } catch (err) {
            if (err instanceof NoFallbackError && bubbleNoFallback) {
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
            res.setHeader("Content-Length", String(byteLength(payload)));
            if (options.generateEtags) {
                res.setHeader("ETag", generateETag(payload));
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