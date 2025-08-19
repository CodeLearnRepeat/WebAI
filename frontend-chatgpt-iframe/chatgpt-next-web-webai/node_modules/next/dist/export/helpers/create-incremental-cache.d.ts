import { IncrementalCache } from '../../server/lib/incremental-cache';
export declare function createIncrementalCache(incrementalCacheHandlerPath: string | undefined, isrMemoryCacheSize: number | undefined, fetchCacheKeyPrefix: string | undefined, distDir: string): IncrementalCache;
