import React from 'react';
import {format} from 'date-fns';


export function parseQuery(qstr) {
    var query = {};
    var a = (qstr[0] === '?' ? qstr.substr(1) : qstr).split('&');
    for (var i = 0; i < a.length; i++) {
        var b = a[i].split('=');
        query[decodeURIComponent(b[0])] = decodeURIComponent(b[1] || '');
    }
    return query;
}


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


// "bind" the given properties statically to a component
export function withProps (Comp, extraProps) {
    return (props) => <Comp {...props} {...extraProps}/>;
}


// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
export function debounce(func, wait, immediate) {
	var timeout;
	return function() {
		var context = this, args = arguments;
		var later = function() {
			timeout = null;
			if (!immediate) func.apply(context, args);
		};
		var callNow = immediate && !timeout;
		clearTimeout(timeout);
		timeout = setTimeout(later, wait);
		if (callNow) func.apply(context, args);
	};
};
