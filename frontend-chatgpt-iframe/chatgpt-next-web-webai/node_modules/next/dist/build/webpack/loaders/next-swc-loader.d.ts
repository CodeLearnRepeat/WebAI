import type { NextConfig } from '../../../../types';
import { type BundleType } from '../../swc/options';
export interface SWCLoaderOptions {
    rootDir: string;
    isServer: boolean;
    pagesDir?: string;
    appDir?: string;
    hasReactRefresh: boolean;
    optimizeServerReact?: boolean;
    nextConfig: NextConfig;
    jsConfig: any;
    supportedBrowsers: string[] | undefined;
    swcCacheDir: string;
    bundleTarget: BundleType;
    hasServerComponents?: boolean;
    isServerLayer: boolean;
}
export declare function pitch(this: any): void;
export default function swcLoader(this: any, inputSource: string, inputSourceMap: any): void;
export declare const raw = true;
