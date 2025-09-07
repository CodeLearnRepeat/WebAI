/// <reference types="react" />
import type { FlightRouterState } from '../app-render/types';
import type RenderResult from '../render-result';
export type ReactReadableStream = ReadableStream<Uint8Array> & {
    allReady?: Promise<void> | undefined;
};
export declare const streamToBufferedResult: (renderResult: RenderResult) => Promise<string>;
export declare function cloneTransformStream(source: TransformStream): TransformStream<any, any>;
export declare function chainStreams<T>(streams: ReadableStream<T>[]): ReadableStream<T>;
export declare function streamFromString(str: string): ReadableStream<Uint8Array>;
export declare function streamToString(stream: ReadableStream<Uint8Array>): Promise<string>;
export declare function createBufferedTransformStream(): TransformStream<Uint8Array, Uint8Array>;
export declare function createInsertedHTMLStream(getServerInsertedHTML: () => Promise<string>): TransformStream<Uint8Array, Uint8Array>;
export declare function renderToInitialFizzStream({ ReactDOMServer, element, streamOptions, }: {
    ReactDOMServer: typeof import('react-dom/server.edge');
    element: React.ReactElement;
    streamOptions?: any;
}): Promise<ReactReadableStream>;
export declare function createRootLayoutValidatorStream(assetPrefix: string | undefined, getTree: () => FlightRouterState): TransformStream<Uint8Array, Uint8Array>;
export declare function continueFizzStream(renderStream: ReactReadableStream, { suffix, inlinedDataStream, generateStaticHTML, getServerInsertedHTML, serverInsertedHTMLToHead, validateRootLayout, }: {
    inlinedDataStream?: ReadableStream<Uint8Array>;
    generateStaticHTML: boolean;
    getServerInsertedHTML?: () => Promise<string>;
    serverInsertedHTMLToHead: boolean;
    validateRootLayout?: {
        assetPrefix?: string;
        getTree: () => FlightRouterState;
    };
    suffix?: string;
}): Promise<ReadableStream<Uint8Array>>;
