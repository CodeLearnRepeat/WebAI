import type { NextConfigComplete } from '../server/config-shared';
export default function loadJsConfig(dir: string, config: NextConfigComplete): Promise<{
    useTypeScript: boolean;
    jsConfig: {
        compilerOptions: Record<string, any>;
    } | undefined;
    resolvedBaseUrl: string | undefined;
}>;
