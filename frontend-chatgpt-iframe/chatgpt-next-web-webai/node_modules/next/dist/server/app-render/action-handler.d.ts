/// <reference types="node" />
import type { IncomingMessage, ServerResponse } from 'http';
import type { SizeLimit } from '../../../types';
import RenderResult from '../render-result';
import type { StaticGenerationStore } from '../../client/components/static-generation-async-storage.external';
import type { RequestStore } from '../../client/components/request-async-storage.external';
import type { AppRenderContext, GenerateFlight } from './app-render';
export declare function handleAction({ req, res, ComponentMod, page, serverActionsManifest, generateFlight, staticGenerationStore, requestStore, serverActionsBodySizeLimit, ctx, }: {
    req: IncomingMessage;
    res: ServerResponse;
    ComponentMod: any;
    page: string;
    serverActionsManifest: any;
    generateFlight: GenerateFlight;
    staticGenerationStore: StaticGenerationStore;
    requestStore: RequestStore;
    serverActionsBodySizeLimit?: SizeLimit;
    ctx: AppRenderContext;
}): Promise<undefined | {
    type: 'not-found';
} | {
    type: 'done';
    result: RenderResult | undefined;
    formState?: any;
}>;
