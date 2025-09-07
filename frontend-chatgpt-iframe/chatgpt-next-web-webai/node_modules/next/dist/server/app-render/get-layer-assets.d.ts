import React from 'react';
import type { AppRenderContext } from './app-render';
export declare function getLayerAssets({ ctx, layoutOrPagePath, injectedCSS: injectedCSSWithCurrentLayout, injectedFontPreloadTags: injectedFontPreloadTagsWithCurrentLayout, }: {
    layoutOrPagePath: string | undefined;
    injectedCSS: Set<string>;
    injectedFontPreloadTags: Set<string>;
    ctx: AppRenderContext;
}): React.ReactNode;
