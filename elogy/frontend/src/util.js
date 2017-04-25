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

