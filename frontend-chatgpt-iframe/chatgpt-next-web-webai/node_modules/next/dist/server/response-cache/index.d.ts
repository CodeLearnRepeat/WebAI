import type { IncrementalCache, ResponseCacheEntry, ResponseGenerator } from './types';
export * from './types';
export default class ResponseCache {
    private readonly batcher;
    private previousCacheItem?;
    private minimalMode?;
    constructor(minimalMode: boolean);
    get(key: string | null, responseGenerator: ResponseGenerator, context: {
        isOnDemandRevalidate?: boolean;
        isPrefetch?: boolean;
        incrementalCache: IncrementalCache;
    }): Promise<ResponseCacheEntry | null>;
}
