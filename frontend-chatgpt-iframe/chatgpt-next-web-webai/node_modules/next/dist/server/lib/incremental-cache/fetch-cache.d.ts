import type { CacheHandler, CacheHandlerContext, CacheHandlerValue } from './';
export default class FetchCache implements CacheHandler {
    private headers;
    private cacheEndpoint?;
    private debug;
    static isAvailable(ctx: {
        _requestHeaders: CacheHandlerContext['_requestHeaders'];
    }): boolean;
    constructor(ctx: CacheHandlerContext);
    revalidateTag(tag: string): Promise<void>;
    get(key: string, ctx: {
        tags?: string[];
        softTags?: string[];
        fetchCache?: boolean;
        fetchUrl?: string;
        fetchIdx?: number;
    }): Promise<CacheHandlerValue | null>;
    set(key: string, data: CacheHandlerValue['value'], { fetchCache, fetchIdx, fetchUrl, tags, }: {
        tags?: string[];
        fetchCache?: boolean;
        fetchUrl?: string;
        fetchIdx?: number;
    }): Promise<void>;
}
