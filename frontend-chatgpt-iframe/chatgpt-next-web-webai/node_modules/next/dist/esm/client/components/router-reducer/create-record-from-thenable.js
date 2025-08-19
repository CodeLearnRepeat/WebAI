/**
 * Create data fetching record for Promise.
 */ export function createRecordFromThenable(promise) {
    const thenable = promise;
    thenable.status = "pending";
    thenable.then((value)=>{
        if (thenable.status === "pending") {
            thenable.status = "fulfilled";
            thenable.value = value;
        }
    }, (err)=>{
        if (thenable.status === "pending") {
            thenable.status = "rejected";
            thenable.reason = err;
        }
    });
    return thenable;
}

//# sourceMappingURL=create-record-from-thenable.js.map