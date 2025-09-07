import { isRedirectError } from "./redirect";
export function getRedirectStatusCodeFromError(error) {
    if (!isRedirectError(error)) {
        throw new Error("Not a redirect error");
    }
    return error.digest.split(";", 4)[3] === "true" ? 308 : 307;
}

//# sourceMappingURL=get-redirect-status-code-from-error.js.map