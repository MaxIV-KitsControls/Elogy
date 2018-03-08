import React from "react";
import { format } from "date-fns";

// parse an URL query string e.g. "?a=1&b=2" into an object
export function parseQuery(qstr) {
    var query = {};
    var a = (qstr[0] === "?" ? qstr.substr(1) : qstr).split("&");
    for (var i = 0; i < a.length; i++) {
        var b = a[i].split("=");
        query[decodeURIComponent(b[0])] = decodeURIComponent(b[1] || "");
    }
    return query;
}

// group a list of items according to the key function, keeping the order
export var groupBy = function(xs, keyFunc) {
    return xs.reduce(function(rv, x) {
        (rv[keyFunc(x)] = rv[keyFunc(x)] || []).push(x);
        return rv;
    }, {});
};

export function formatDateTimeString(timestamp) {
    return format(new Date(Date.parse(timestamp)), "HH:mm:ss, ddd MMM D YYYY");
}

export function formatTimeString(timestamp) {
    return format(new Date(Date.parse(timestamp)), "HH:mm:ss");
}

export function formatDateString(timestamp) {
    return format(new Date(Date.parse(timestamp)), "ddd MMM D YYYY");
}

// "bind" the given extra props statically to a React component
export function withProps(Comp, extraProps) {
    return props => <Comp {...props} {...extraProps} />;
}

// Wraps a function so that calling it delays the execution for 'wait'
// milliseconds.  If the wrapper is called again before that, the
// timer is reset. If the 'immediate' argument is true, the function
// is called at the first run, but not again until the wrapper has not
// been called for 'wait' ms.
export function debounce(func, wait, immediate) {
    let timeout;
    return function() {
        let context = this,
            args = arguments;
        let later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        let callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}
