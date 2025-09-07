"use strict";
Object.defineProperty(exports, "__esModule", {
    value: true
});
Object.defineProperty(exports, "readRecordValue", {
    enumerable: true,
    get: function() {
        return readRecordValue;
    }
});
function readRecordValue(thenable) {
    if (thenable.status === "fulfilled") {
        return thenable.value;
    } else {
        throw thenable;
    }
}

if ((typeof exports.default === 'function' || (typeof exports.default === 'object' && exports.default !== null)) && typeof exports.default.__esModule === 'undefined') {
  Object.defineProperty(exports.default, '__esModule', { value: true });
  Object.assign(exports.default, exports);
  module.exports = exports.default;
}

//# sourceMappingURL=read-record-value.js.map