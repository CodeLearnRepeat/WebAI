import type { AppRenderContext } from './app-render';
export declare function createComponentAndStyles({ filePath, getComponent, injectedCSS, ctx, }: {
    filePath: string;
    getComponent: () => any;
    injectedCSS: Set<string>;
    ctx: AppRenderContext;
}): Promise<any>;
