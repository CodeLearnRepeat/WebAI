import React from 'react';
import type { LoaderTree } from '../lib/app-dir-module';
import type { CreateSegmentPath, AppRenderContext } from './app-render';
/**
 * Use the provided loader tree to create the React Component tree.
 */
export declare function createComponentTree({ createSegmentPath, loaderTree: tree, parentParams, firstItem, rootLayoutIncluded, injectedCSS, injectedFontPreloadTags, asNotFound, metadataOutlet, ctx, }: {
    createSegmentPath: CreateSegmentPath;
    loaderTree: LoaderTree;
    parentParams: {
        [key: string]: any;
    };
    rootLayoutIncluded: boolean;
    firstItem?: boolean;
    injectedCSS: Set<string>;
    injectedFontPreloadTags: Set<string>;
    asNotFound?: boolean;
    metadataOutlet?: React.ReactNode;
    ctx: AppRenderContext;
}): Promise<{
    Component: React.ComponentType;
    styles: React.ReactNode;
}>;
