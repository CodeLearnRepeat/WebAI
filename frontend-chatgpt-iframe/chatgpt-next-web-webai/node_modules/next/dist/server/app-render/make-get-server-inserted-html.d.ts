import React from 'react';
export declare function makeGetServerInsertedHTML({ polyfills, renderServerInsertedHTML, }: {
    polyfills: JSX.IntrinsicElements['script'][];
    renderServerInsertedHTML: () => React.ReactNode;
}): (serverCapturedErrors: Error[]) => Promise<string>;
