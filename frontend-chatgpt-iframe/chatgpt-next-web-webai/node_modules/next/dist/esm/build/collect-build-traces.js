import { Span } from "../trace";
import { TRACE_IGNORES, getFilesMapFromReasons } from "./webpack/plugins/next-trace-entrypoints-plugin";
import { TRACE_OUTPUT_VERSION, TURBO_TRACE_DEFAULT_MEMORY_LIMIT } from "../shared/lib/constants";
import path from "path";
import fs from "fs/promises";
import { loadBindings } from "./swc";
import { nonNullable } from "../lib/non-nullable";
import * as ciEnvironment from "../telemetry/ci-info";
import debugOriginal from "next/dist/compiled/debug";
import { isMatch } from "next/dist/compiled/micromatch";
import { defaultOverrides } from "../server/require-hook";
import { nodeFileTrace } from "next/dist/compiled/@vercel/nft";
import { normalizePagePath } from "../shared/lib/page-path/normalize-page-path";
import { normalizeAppPath } from "../shared/lib/router/utils/app-paths";
import isError from "../lib/is-error";
const debug = debugOriginal("next:build:build-traces");
export async function collectBuildTraces({ dir, config, distDir, pageKeys, pageInfos, staticPages, nextBuildSpan = new Span({
    name: "build"
}), hasSsrAmpPages, buildTraceContext, outputFileTracingRoot }) {
    const startTime = Date.now();
    debug("starting build traces");
    let turboTasksForTrace;
    let bindings = await loadBindings();
    const runTurbotrace = async function() {
        if (!config.experimental.turbotrace || !buildTraceContext) {
            return;
        }
        if (!(bindings == null ? void 0 : bindings.isWasm) && typeof bindings.turbo.startTrace === "function") {
            var _config_experimental_turbotrace;
            let turbotraceOutputPath;
            let turbotraceFiles;
            turboTasksForTrace = bindings.turbo.createTurboTasks((((_config_experimental_turbotrace = config.experimental.turbotrace) == null ? void 0 : _config_experimental_turbotrace.memoryLimit) ?? TURBO_TRACE_DEFAULT_MEMORY_LIMIT) * 1024 * 1024);
            const { entriesTrace, chunksTrace } = buildTraceContext;
            if (entriesTrace) {
                const { appDir: buildTraceContextAppDir, depModArray, entryNameMap, outputPath, action } = entriesTrace;
                const depModSet = new Set(depModArray);
                const filesTracedInEntries = await bindings.turbo.startTrace(action, turboTasksForTrace);
                const { contextDirectory, input: entriesToTrace } = action;
                // only trace the assets under the appDir
                // exclude files from node_modules, entries and processed by webpack
                const filesTracedFromEntries = filesTracedInEntries.map((f)=>path.join(contextDirectory, f)).filter((f)=>!f.includes("/node_modules/") && f.startsWith(buildTraceContextAppDir) && !entriesToTrace.includes(f) && !depModSet.has(f));
                if (filesTracedFromEntries.length) {
                    // The turbo trace doesn't provide the traced file type and reason at present
                    // let's write the traced files into the first [entry].nft.json
                    const [[, entryName]] = Array.from(Object.entries(entryNameMap)).filter(([k])=>k.startsWith(buildTraceContextAppDir));
                    const traceOutputPath = path.join(outputPath, `../${entryName}.js.nft.json`);
                    const traceOutputDir = path.dirname(traceOutputPath);
                    turbotraceOutputPath = traceOutputPath;
                    turbotraceFiles = filesTracedFromEntries.map((file)=>path.relative(traceOutputDir, file));
                }
            }
            if (chunksTrace) {
                const { action, outputPath } = chunksTrace;
                action.input = action.input.filter((f)=>{
                    const outputPagesPath = path.join(outputPath, "..", "pages");
                    return !f.startsWith(outputPagesPath) || !staticPages.includes(// strip `outputPagesPath` and file ext from absolute
                    f.substring(outputPagesPath.length, f.length - 3));
                });
                await bindings.turbo.startTrace(action, turboTasksForTrace);
                if (turbotraceOutputPath && turbotraceFiles) {
                    const existedNftFile = await fs.readFile(turbotraceOutputPath, "utf8").then((existedContent)=>JSON.parse(existedContent)).catch(()=>({
                            version: TRACE_OUTPUT_VERSION,
                            files: []
                        }));
                    existedNftFile.files.push(...turbotraceFiles);
                    const filesSet = new Set(existedNftFile.files);
                    existedNftFile.files = [
                        ...filesSet
                    ];
                    await fs.writeFile(turbotraceOutputPath, JSON.stringify(existedNftFile), "utf8");
                }
            }
        }
    };
    const { outputFileTracingIncludes = {}, outputFileTracingExcludes = {} } = config.experimental;
    const excludeGlobKeys = Object.keys(outputFileTracingExcludes);
    await nextBuildSpan.traceChild("node-file-trace-build").traceAsyncFn(async ()=>{
        var _config_experimental_turbotrace, _config_experimental;
        const nextServerTraceOutput = path.join(distDir, "next-server.js.nft.json");
        const nextMinimalTraceOutput = path.join(distDir, "next-minimal-server.js.nft.json");
        const root = ((_config_experimental = config.experimental) == null ? void 0 : (_config_experimental_turbotrace = _config_experimental.turbotrace) == null ? void 0 : _config_experimental_turbotrace.contextDirectory) ?? outputFileTracingRoot;
        // Under standalone mode, we need to trace the extra IPC server and
        // worker files.
        const isStandalone = config.output === "standalone";
        const nextServerEntry = require.resolve("next/dist/server/next-server");
        const sharedEntriesSet = [
            ...config.experimental.turbotrace ? [] : Object.keys(defaultOverrides).map((value)=>require.resolve(value, {
                    paths: [
                        require.resolve("next/dist/server/require-hook")
                    ]
                })),
            require.resolve("next/dist/compiled/next-server/app-page.runtime.prod"),
            require.resolve("next/dist/compiled/next-server/app-route.runtime.prod"),
            require.resolve("next/dist/compiled/next-server/pages.runtime.prod"),
            require.resolve("next/dist/compiled/next-server/pages-api.runtime.prod")
        ];
        const { incrementalCacheHandlerPath } = config.experimental;
        // ensure we trace any dependencies needed for custom
        // incremental cache handler
        if (incrementalCacheHandlerPath) {
            sharedEntriesSet.push(require.resolve(path.isAbsolute(incrementalCacheHandlerPath) ? incrementalCacheHandlerPath : path.join(dir, incrementalCacheHandlerPath)));
        }
        const serverEntries = [
            ...sharedEntriesSet,
            ...isStandalone ? [
                require.resolve("next/dist/server/lib/start-server"),
                require.resolve("next/dist/server/next"),
                require.resolve("next/dist/server/require-hook")
            ] : [],
            require.resolve("next/dist/server/next-server")
        ].filter(Boolean);
        const minimalServerEntries = [
            ...sharedEntriesSet,
            require.resolve("next/dist/compiled/next-server/server.runtime.prod")
        ].filter(Boolean);
        const additionalIgnores = new Set();
        for (const glob of excludeGlobKeys){
            if (isMatch("next-server", glob)) {
                outputFileTracingExcludes[glob].forEach((exclude)=>{
                    additionalIgnores.add(exclude);
                });
            }
        }
        const serverIgnores = [
            "**/*.d.ts",
            "**/*.map",
            isStandalone ? null : "**/next/dist/compiled/jest-worker/**/*",
            "**/next/dist/compiled/webpack/(bundle4|bundle5).js",
            "**/node_modules/webpack5/**/*",
            "**/next/dist/server/lib/squoosh/**/*.wasm",
            "**/next/dist/server/lib/route-resolver*",
            "**/next/dist/pages/**/*",
            ...ciEnvironment.hasNextSupport ? [
                // only ignore image-optimizer code when
                // this is being handled outside of next-server
                "**/next/dist/server/image-optimizer.js",
                "**/node_modules/sharp/**/*"
            ] : [],
            ...!hasSsrAmpPages ? [
                "**/next/dist/compiled/@ampproject/toolbox-optimizer/**/*"
            ] : [],
            ...additionalIgnores,
            ...isStandalone ? [] : TRACE_IGNORES,
            ...config.experimental.outputFileTracingIgnores || []
        ].filter(nonNullable);
        const serverIgnoreFn = (pathname)=>{
            if (path.isAbsolute(pathname) && !pathname.startsWith(root)) {
                return true;
            }
            return isMatch(pathname, serverIgnores, {
                contains: true,
                dot: true
            });
        };
        const traceContext = path.join(nextServerEntry, "..", "..");
        const serverTracedFiles = new Set();
        const minimalServerTracedFiles = new Set();
        function addToTracedFiles(base, file, dest) {
            dest.add(path.relative(distDir, path.join(base, file)).replace(/\\/g, "/"));
        }
        if (isStandalone) {
            addToTracedFiles("", require.resolve("next/dist/compiled/jest-worker/processChild"), serverTracedFiles);
            addToTracedFiles("", require.resolve("next/dist/compiled/jest-worker/threadChild"), serverTracedFiles);
        }
        if (config.experimental.turbotrace) {
            await runTurbotrace();
            const startTrace = bindings.turbo.startTrace;
            const makeTrace = async (entries)=>{
                var _config_experimental_turbotrace, _config_experimental_turbotrace1, _config_experimental_turbotrace2, _config_experimental_turbotrace3;
                return startTrace({
                    action: "print",
                    input: entries,
                    contextDirectory: traceContext,
                    logLevel: (_config_experimental_turbotrace = config.experimental.turbotrace) == null ? void 0 : _config_experimental_turbotrace.logLevel,
                    processCwd: (_config_experimental_turbotrace1 = config.experimental.turbotrace) == null ? void 0 : _config_experimental_turbotrace1.processCwd,
                    logDetail: (_config_experimental_turbotrace2 = config.experimental.turbotrace) == null ? void 0 : _config_experimental_turbotrace2.logDetail,
                    showAll: (_config_experimental_turbotrace3 = config.experimental.turbotrace) == null ? void 0 : _config_experimental_turbotrace3.logAll
                }, turboTasksForTrace);
            };
            // turbotrace does not handle concurrent tracing
            const vanillaFiles = await makeTrace(serverEntries);
            const minimalFiles = await makeTrace(minimalServerEntries);
            for (const [set, files] of [
                [
                    serverTracedFiles,
                    vanillaFiles
                ],
                [
                    minimalServerTracedFiles,
                    minimalFiles
                ]
            ]){
                for (const file of files){
                    if (!serverIgnoreFn(path.join(traceContext, file))) {
                        addToTracedFiles(traceContext, file, set);
                    }
                }
            }
        } else {
            var _buildTraceContext_chunksTrace;
            const chunksToTrace = [
                ...(buildTraceContext == null ? void 0 : (_buildTraceContext_chunksTrace = buildTraceContext.chunksTrace) == null ? void 0 : _buildTraceContext_chunksTrace.action.input) || [],
                ...serverEntries,
                ...minimalServerEntries
            ];
            const result = await nodeFileTrace(chunksToTrace, {
                base: outputFileTracingRoot,
                processCwd: dir,
                mixedModules: true,
                async readFile (p) {
                    try {
                        return await fs.readFile(p, "utf8");
                    } catch (e) {
                        if (isError(e) && (e.code === "ENOENT" || e.code === "EISDIR")) {
                            // handle temporary internal webpack files
                            if (p.match(/static[/\\]media/)) {
                                return "";
                            }
                            return null;
                        }
                        throw e;
                    }
                },
                async readlink (p) {
                    try {
                        return await fs.readlink(p);
                    } catch (e) {
                        if (isError(e) && (e.code === "EINVAL" || e.code === "ENOENT" || e.code === "UNKNOWN")) {
                            return null;
                        }
                        throw e;
                    }
                },
                async stat (p) {
                    try {
                        return await fs.stat(p);
                    } catch (e) {
                        if (isError(e) && (e.code === "ENOENT" || e.code === "ENOTDIR")) {
                            return null;
                        }
                        throw e;
                    }
                }
            });
            const reasons = result.reasons;
            const fileList = result.fileList;
            for (const file of result.esmFileList){
                fileList.add(file);
            }
            const parentFilesMap = getFilesMapFromReasons(fileList, reasons);
            for (const [entries, tracedFiles] of [
                [
                    serverEntries,
                    serverTracedFiles
                ],
                [
                    minimalServerEntries,
                    minimalServerTracedFiles
                ]
            ]){
                for (const file of entries){
                    const curFiles = parentFilesMap.get(path.relative(outputFileTracingRoot, file));
                    tracedFiles.add(path.relative(distDir, file).replace(/\\/g, "/"));
                    for (const curFile of curFiles || []){
                        const filePath = path.join(outputFileTracingRoot, curFile);
                        if (!serverIgnoreFn(filePath)) {
                            tracedFiles.add(path.relative(distDir, filePath).replace(/\\/g, "/"));
                        }
                    }
                }
            }
            const { entryNameFilesMap } = (buildTraceContext == null ? void 0 : buildTraceContext.chunksTrace) || {};
            await Promise.all([
                ...entryNameFilesMap ? Object.entries(entryNameFilesMap) : new Map()
            ].map(async ([entryName, entryNameFiles])=>{
                const isApp = entryName.startsWith("app/");
                const isPages = entryName.startsWith("pages/");
                let route = entryName;
                if (isApp) {
                    route = normalizeAppPath(route.substring("app".length));
                }
                if (isPages) {
                    route = normalizePagePath(route.substring("pages".length));
                }
                // we don't need to trace for automatically statically optimized
                // pages as they don't have server bundles
                if (staticPages.includes(route)) {
                    return;
                }
                const entryOutputPath = path.join(distDir, "server", `${entryName}.js`);
                const traceOutputPath = `${entryOutputPath}.nft.json`;
                const existingTrace = JSON.parse(await fs.readFile(traceOutputPath, "utf8"));
                const traceOutputDir = path.dirname(traceOutputPath);
                const curTracedFiles = new Set();
                for (const file of [
                    ...entryNameFiles,
                    entryOutputPath
                ]){
                    const curFiles = parentFilesMap.get(path.relative(outputFileTracingRoot, file));
                    for (const curFile of curFiles || []){
                        curTracedFiles.add(path.relative(traceOutputDir, path.join(outputFileTracingRoot, curFile)).replace(/\\/g, "/"));
                    }
                }
                for (const file of existingTrace.files || []){
                    curTracedFiles.add(file);
                }
                await fs.writeFile(traceOutputPath, JSON.stringify({
                    ...existingTrace,
                    files: [
                        ...curTracedFiles
                    ].sort()
                }));
            }));
        }
        const moduleTypes = [
            "app-page",
            "pages"
        ];
        for (const type of moduleTypes){
            const modulePath = require.resolve(`next/dist/server/future/route-modules/${type}/module.compiled`);
            const relativeModulePath = path.relative(root, modulePath);
            const contextDir = path.join(path.dirname(modulePath), "vendored", "contexts");
            for (const item of (await fs.readdir(contextDir))){
                const itemPath = path.relative(root, path.join(contextDir, item));
                addToTracedFiles(root, itemPath, serverTracedFiles);
                addToTracedFiles(root, itemPath, minimalServerTracedFiles);
            }
            addToTracedFiles(root, relativeModulePath, serverTracedFiles);
            addToTracedFiles(root, relativeModulePath, minimalServerTracedFiles);
        }
        await Promise.all([
            fs.writeFile(nextServerTraceOutput, JSON.stringify({
                version: 1,
                files: Array.from(serverTracedFiles)
            })),
            fs.writeFile(nextMinimalTraceOutput, JSON.stringify({
                version: 1,
                files: Array.from(minimalServerTracedFiles)
            }))
        ]);
    });
    const includeExcludeSpan = nextBuildSpan.traceChild("apply-include-excludes");
    const resolvedTraceIncludes = new Map();
    const includeGlobKeys = Object.keys(outputFileTracingIncludes);
    await includeExcludeSpan.traceAsyncFn(async ()=>{
        const globOrig = require("next/dist/compiled/glob");
        const glob = (pattern)=>{
            return new Promise((resolve, reject)=>{
                globOrig(pattern, {
                    cwd: dir,
                    nodir: true,
                    dot: true
                }, (err, files)=>{
                    if (err) {
                        return reject(err);
                    }
                    resolve(files);
                });
            });
        };
        for (let page of pageKeys.pages){
            // edge routes have no trace files
            const [, pageInfo] = pageInfos.find((item)=>item[0] === page) || [];
            if ((pageInfo == null ? void 0 : pageInfo.runtime) === "edge") {
                continue;
            }
            const combinedIncludes = new Set();
            const combinedExcludes = new Set();
            page = normalizePagePath(page);
            for (const curGlob of includeGlobKeys){
                if (isMatch(page, [
                    curGlob
                ], {
                    dot: true,
                    contains: true
                })) {
                    for (const include of outputFileTracingIncludes[curGlob]){
                        combinedIncludes.add(include.replace(/\\/g, "/"));
                    }
                }
            }
            for (const curGlob of excludeGlobKeys){
                if (isMatch(page, [
                    curGlob
                ], {
                    dot: true,
                    contains: true
                })) {
                    for (const exclude of outputFileTracingExcludes[curGlob]){
                        combinedExcludes.add(exclude);
                    }
                }
            }
            if (!(combinedIncludes == null ? void 0 : combinedIncludes.size) && !(combinedExcludes == null ? void 0 : combinedExcludes.size)) {
                continue;
            }
            const traceFile = path.join(distDir, "server/pages", `${page}.js.nft.json`);
            const pageDir = path.dirname(traceFile);
            const traceContent = JSON.parse(await fs.readFile(traceFile, "utf8"));
            const includes = [];
            if (combinedIncludes == null ? void 0 : combinedIncludes.size) {
                await Promise.all([
                    ...combinedIncludes
                ].map(async (includeGlob)=>{
                    const results = await glob(includeGlob);
                    const resolvedInclude = resolvedTraceIncludes.get(includeGlob) || [
                        ...results.map((file)=>{
                            return path.relative(pageDir, path.join(dir, file));
                        })
                    ];
                    includes.push(...resolvedInclude);
                    resolvedTraceIncludes.set(includeGlob, resolvedInclude);
                }));
            }
            const combined = new Set([
                ...traceContent.files,
                ...includes
            ]);
            if (combinedExcludes == null ? void 0 : combinedExcludes.size) {
                const resolvedGlobs = [
                    ...combinedExcludes
                ].map((exclude)=>path.join(dir, exclude));
                combined.forEach((file)=>{
                    if (isMatch(path.join(pageDir, file), resolvedGlobs, {
                        dot: true,
                        contains: true
                    })) {
                        combined.delete(file);
                    }
                });
            }
            await fs.writeFile(traceFile, JSON.stringify({
                version: traceContent.version,
                files: [
                    ...combined
                ]
            }));
        }
    });
    debug(`finished build tracing ${Date.now() - startTime}ms`);
}

//# sourceMappingURL=collect-build-traces.js.map