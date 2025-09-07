import type { ThenableRecord } from './router-reducer-types';
/**
 * Create data fetching record for Promise.
 */
export declare function createRecordFromThenable<T>(promise: PromiseLike<T>): ThenableRecord<T>;
