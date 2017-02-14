/*
A very simple "router" that keeps the hash part of the URL in sync with
the iframes in the page. The point is to make the browser URL useful
so that history and bookmarks work.

The global hash is a concatenation of the iframe URLs.
*/

window.Router = (function () {

    function Router(iframeNames) {

        var iframes = iframeNames.map(function (iframeName) {
            var iframe = document.querySelector('object[name="'+iframeName+'"]');
            iframe.addEventListener("load", handleIframeLoad)
            return iframe;
        });

        handleHashChange();
        
        window.addEventListener("hashchange", handleHashChange);
        
        function handleHashChange() {

            // Detect changes in the global hash

            if (window.location.hash == "" || window.location.hash == "#") return

            // Using @ as a separator may or may not be a good idea, but
            // it's a character that's allowed it URLs and not used for
            // anything special, usually. AFAICT.
            var iframeUrls = window.location.hash.slice(1).split("@")

            for (var i=0; i<iframeUrls.length; i++) {
                // set the iframe URL, if it has changed
                var oldUrl = (iframes[i].contentDocument.location.pathname +
                              iframes[i].contentDocument.location.search)
                if (iframeUrls[i].split("#")[0] == "/") {
                    // we never want to show the whole UI in one frame!
                    // TODO: this is a hack.
                    continue
                }
                if (oldUrl != iframeUrls[i]) {
                    iframes[i].contentDocument.location = iframeUrls[i];
                }

                // if we're switching logbook or entry, send out a signal
                var path = /^\/([^\/]+)\/(\d+)/.exec(iframeUrls[i]);
                if (path && eventbus[path[1]]) {
                    var iframeName = path[1],
                        contentId = path[2];
                    if (eventbus[iframeName]) {
                        eventbus[iframeName].dispatch(contentId);
                    }
                }                
            }
        }

        function handleIframeLoad(event) {

            // Detect URL changes in any of the iframes
            
            var urlHash = [], reload;
            for (var i=0; i<iframes.length; i++) {
                var iframe = iframes[i],
                    location = iframe.contentDocument.location;

                if (location.pathname == "/") {
                    urlHash.push("about:blank");
                    continue;
                }
                
                // This is a way to signal the router that there's a new
                // entry, which means that the whole page needs to reload,
                // to update the list of entries etc
                reload = location.search.slice(0, 5) == "?new=";
                if (reload) {
                    var newEntry = location.search.slice(5);
                    urlHash.push(location.pathname + "#" + newEntry);
                } else {
                    urlHash.push(location.pathname + location.search);
                }
            }

            if (urlHash.length > 0) {
                window.location.hash = urlHash.join("@");
                if (reload) {
                    window.location.reload();
                }
            }
            
        }
        
    };
    
    return Router;
    
})();
