/// <reference types="react" />
import type { CacheNode } from '../../../shared/lib/app-router-context.shared-runtime';
import type { FlightRouterState } from '../../../server/app-render/types';
export declare function fillLazyItemsTillLeafWithHead(newCache: CacheNode, existingCache: CacheNode | undefined, routerState: FlightRouterState, head: React.ReactNode, wasPrefetched?: boolean): void;
