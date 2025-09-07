import type { BuildManifest } from '../get-page-files';
export declare function getRequiredScripts(buildManifest: BuildManifest, assetPrefix: string, crossOrigin: string | undefined, SRIManifest: undefined | Record<string, string>, qs: string, nonce: string | undefined): [
    () => void,
    {
        src: string;
        integrity?: string;
        crossOrigin?: string | undefined;
    }
];
