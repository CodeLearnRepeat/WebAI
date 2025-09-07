import type { ThenableRecord } from './router-reducer/router-reducer-types';
export declare class PromiseQueue {
    #private;
    constructor(maxConcurrency?: number);
    enqueue<T>(promiseFn: () => Promise<T>): Promise<T>;
    bump(promiseFn: ThenableRecord<any> | Promise<any>): void;
}
