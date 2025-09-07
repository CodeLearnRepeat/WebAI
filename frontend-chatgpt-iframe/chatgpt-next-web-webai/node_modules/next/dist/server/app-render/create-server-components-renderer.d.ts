/// <reference types="react" />
import type { RenderOpts } from './types';
import type { AppPageModule } from '../future/route-modules/app-page/module';
import type { createErrorHandler } from './create-error-handler';
/**
 * Create a component that renders the Flight stream.
 * This is only used for renderToHTML, the Flight response does not need additional wrappers.
 */
export declare function createServerComponentRenderer<Props>(ComponentToRender: (props: Props) => any, ComponentMod: AppPageModule, { inlinedDataTransformStream, clientReferenceManifest, serverContexts, formState, }: {
    inlinedDataTransformStream: TransformStream<Uint8Array, Uint8Array>;
    clientReferenceManifest: NonNullable<RenderOpts['clientReferenceManifest']>;
    serverContexts: Array<[
        ServerContextName: string,
        JSONValue: Object | number | string
    ]>;
    formState: null | any;
}, serverComponentsErrorHandler: ReturnType<typeof createErrorHandler>, nonce?: string): (props: Props) => JSX.Element;
