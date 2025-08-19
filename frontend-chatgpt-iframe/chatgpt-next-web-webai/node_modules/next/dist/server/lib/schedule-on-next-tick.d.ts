export type ScheduledFn<T = void> = () => T | PromiseLike<T>;
export type SchedulerFn<T = void> = (cb: ScheduledFn<T>) => void;
/**
 * Schedules a function to be called on the next tick after the other promises
 * have been resolved.
 */
export declare const scheduleOnNextTick: <T = void>(cb: ScheduledFn<T>) => void;
