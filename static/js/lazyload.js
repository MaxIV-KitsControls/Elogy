/*
Lazily loads images as they scroll into view.

Takes a container element which is assumed to contain img elements.
The img elements must have the "lazy" class, and its "data-src" attribute
set to the actual src of the image. src can be empty or set to some 
placeholder image.
*/

window.LazyImageLoad = (function () {

    function LazyImageLoad (container) {
        this.container = container;
        this.images = Array.prototype.slice.call(
            container.querySelectorAll("img.lazy"));
        // Debouncing means that images won't start loading until
        // after scrolling has stopped for a moment.
        container.addEventListener("scroll",
                                   debounce(handleScroll.bind(this), 100));
        handleScroll.bind(this)();
    }
    
    function handleScroll() {
        for (var i = 0; i<this.images.length; i++) {
            var img = this.images[i];
            if (elementInViewport(img, this.container)) {
                img.removeAttribute("width")
                img.src = img.getAttribute("data-src");
                this.images.splice(i, 1)
                i--;  // ahem!
            }
        }
    }

    function elementInViewport(el, container) {
        var rect = el.getBoundingClientRect();
        // load images that are slightly outside the view too
        return rect.bottom >= -100 &&
            rect.top <= container.offsetHeight + 100;
    }

    function debounce(func, wait, immediate) {
        // Takes a function <func>, and calls it after <wait> seconds
        // unless it is called again within that time. In that case
        // the timer is reset.
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

    return LazyImageLoad;
    
})();
