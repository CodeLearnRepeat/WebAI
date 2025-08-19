import type { ExportRouteResult, FileWriter } from '../types';
import type { RenderOpts } from '../../server/app-render/types';
import type { NextParsedUrlQuery } from '../../server/request-meta';
import type { MockedRequest, MockedResponse } from '../../server/lib/mock-request';
export declare const enum ExportedAppPageFiles {
    HTML = "HTML",
    FLIGHT = "FLIGHT",
    META = "META",
    POSTPONED = "POSTPONED"
}
export declare function generatePrefetchRsc(req: MockedRequest, path: string, res: MockedResponse, pathname: string, htmlFilepath: string, renderOpts: RenderOpts, fileWriter: FileWriter): Promise<void>;
export declare function exportAppPage(req: MockedRequest, res: MockedResponse, page: string, path: string, pathname: string, query: NextParsedUrlQuery, renderOpts: RenderOpts, htmlFilepath: string, debugOutput: boolean, isDynamicError: boolean, isAppPrefetch: boolean, fileWriter: FileWriter): Promise<ExportRouteResult>;
