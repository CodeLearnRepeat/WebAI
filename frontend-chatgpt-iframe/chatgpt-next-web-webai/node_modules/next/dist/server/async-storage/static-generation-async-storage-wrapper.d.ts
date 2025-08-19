import type { AsyncStorageWrapper } from './async-storage-wrapper';
import type { StaticGenerationStore } from '../../client/components/static-generation-async-storage.external';
import type { IncrementalCache } from '../lib/incremental-cache';
export type StaticGenerationContext = {
    urlPathname: string;
    renderOpts: {
        originalPathname?: string;
        incrementalCache?: IncrementalCache;
        supportsDynamicHTML: boolean;
        isRevalidate?: boolean;
        isOnDemandRevalidate?: boolean;
        isBot?: boolean;
        isPrefetch?: boolean;
        nextExport?: boolean;
        fetchCache?: StaticGenerationStore['fetchCache'];
        isDraftMode?: boolean;
        isServerAction?: boolean;
        waitUntil?: Promise<any>;
    };
};
export declare const StaticGenerationAsyncStorageWrapper: AsyncStorageWrapper<StaticGenerationStore, StaticGenerationContext>;
