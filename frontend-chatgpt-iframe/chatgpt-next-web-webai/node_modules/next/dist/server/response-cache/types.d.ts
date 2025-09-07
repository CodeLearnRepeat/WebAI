/// <reference types="node" />
/// <reference types="node" />
import type { OutgoingHttpHeaders } from 'http';
import type RenderResult from '../render-result';
import type { Revalidate } from '../lib/revalidate';
export interface ResponseCacheBase {
    get(key: string | null, responseGenerator: ResponseGenerator, context: {
        isOnDemandRevalidate?: boolean;
        isPrefetch?: boolean;
        incrementalCache: IncrementalCache;
    }): Promise<ResponseCacheEntry | null>;
}
export interface CachedFetchValue {
    kind: 'FETCH';
    data: {
        headers: {
            [k: string]: string;
        };
        body: string;
        url: string;
        status?: number;
        tags?: string[];
    };
    revalidate: number;
}
export interface CachedRedirectValue {
    kind: 'REDIRECT';
    props: Object;
}
interface CachedPageValue {
    kind: 'PAGE';
    html: RenderResult;
    pageData: Object;
    status?: number;
    headers?: OutgoingHttpHeaders;
}
export interface CachedRouteValue {
    kind: 'ROUTE';
    body: Buffer;
    status: number;
    headers: OutgoingHttpHeaders;
}
export interface CachedImageValue {
    kind: 'IMAGE';
    etag: string;
    buffer: Buffer;
    extension: string;
    isMiss?: boolean;
    isStale?: boolean;
}
interface IncrementalCachedPageValue {
    kind: 'PAGE';
    html: string;
    pageData: Object;
    headers?: OutgoingHttpHeaders;
    status?: number;
}
export type IncrementalCacheEntry = {
    curRevalidate?: Revalidate;
    revalidateAfter: Revalidate;
    isStale?: boolean | -1;
    value: IncrementalCacheValue | null;
};
export type IncrementalCacheValue = CachedRedirectValue | IncrementalCachedPageValue | CachedImageValue | CachedFetchValue | CachedRouteValue;
export type ResponseCacheValue = CachedRedirectValue | CachedPageValue | CachedImageValue | CachedRouteValue;
export type ResponseCacheEntry = {
    revalidate?: Revalidate;
    value: ResponseCacheValue | null;
    isStale?: boolean | -1;
    isMiss?: boolean;
};
export type ResponseGenerator = (hasResolved: boolean, cacheEntry?: IncrementalCacheItem) => Promise<ResponseCacheEntry | null>;
export type IncrementalCacheItem = {
    revalidateAfter?: number | false;
    curRevalidate?: number | false;
    revalidate?: number | false;
    value: IncrementalCacheValue | null;
    isStale?: boolean | -1;
    isMiss?: boolean;
} | null;
export interface IncrementalCache {
    get: (key: string, ctx?: {
        fetchCache?: boolean;
    }) => Promise<IncrementalCacheItem>;
    set: (key: string, data: IncrementalCacheValue | null, ctx: {
        revalidate: Revalidate;
    }) => Promise<void>;
}
export {};
