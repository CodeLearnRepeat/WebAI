/**
 * Read record value or throw Promise if it's not resolved yet.
 */ export function readRecordValue(thenable) {
    if (thenable.status === "fulfilled") {
        return thenable.value;
    } else {
        throw thenable;
    }
}

//# sourceMappingURL=read-record-value.js.map