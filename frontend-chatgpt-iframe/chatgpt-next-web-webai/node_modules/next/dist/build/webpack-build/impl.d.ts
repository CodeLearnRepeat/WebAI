import type { COMPILER_INDEXES } from '../../shared/lib/constants';
import { NextBuildContext } from '../build-context';
import type { BuildTraceContext } from '../webpack/plugins/next-trace-entrypoints-plugin';
export declare function webpackBuildImpl(compilerName?: keyof typeof COMPILER_INDEXES): Promise<{
    duration: number;
    pluginState: any;
    buildTraceContext?: BuildTraceContext;
}>;
export declare function workerMain(workerData: {
    compilerName: keyof typeof COMPILER_INDEXES;
    buildContext: typeof NextBuildContext;
}): Promise<{
    duration: number;
    pluginState: any;
    buildTraceContext?: BuildTraceContext | undefined;
}>;
