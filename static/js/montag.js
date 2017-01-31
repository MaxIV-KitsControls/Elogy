/* 
Provides simple "tag" like functionality to forms. Basically maintains
a list of input fields that are added/removed as they are filled in.
Useful for editing a variable number of string items, e.g. authors.

Usage:

new Montag(container, {name: "myfield", classes: ["myclass"], placeholder: "Enter something!"});

All options except "name" may be omitted.

The container should be a <fieldset> tag that may contain prefilled
inputs. They should all have the name attribute set to "myfield".

After submitting, contents of the inputs will be available in the form
data under the field "myfield", as a list of strings.

*/

// TODO: There's some issue in chrome, empty inputs don't get removed
// immediately. Probably something with events or keycodes not being
// the same as in FF?

Montag = (function () {

    function Montag(element, config) {
        this.container = element;
        this.form = element.form;
        this.config = config;

        // make sure pre-existing inputs are 
        this.container.querySelectorAll("input")
            .forEach(autosizeInput)
        
        addInput(this.container, this.config);  // add initial empty item
 
        // intercept keypresses to add some neat navigation
        this.container.addEventListener("keypress", function (event) {
            if (event.target.parentNode == element) {
                if (event.keyCode === 13  // return
                    || event.charCode == 44) {  // comma
                    if (splitInput(event.target, config)) {
                        focusNextInput(event.target);
                    }
                    event.preventDefault();
                } else if (event.keyCode === 8  // backspace
                    || event.keyCode === 46) {  // delete
                    setTimeout(function () {removeIfEmpty(event.target);});
                } else if (event.keyCode === 37
                    && event.target.selectionStart === 0) {
                    focusPrevInput(event.target);
                    event.preventDefault();
                } else if (event.keyCode === 39
                    && event.target.selectionStart === event.target.value.length) {
                    focusNextInput(event.target);
                    event.preventDefault();
                } else {
                    event.target.name = config.name;
                }
            }
        });

        // add and remove fields as we go
        this.container.addEventListener("input", onInput.bind(this), true)
        this.container.addEventListener("blur", onBlur.bind(this), true);
    }

    // split an input field into two, at the cursor position
    function splitInput(input, config) {
        if (input.value.length === 0)
            return false;
        var cursorPosition = input.selectionStart;
        var newInput = addInput(input.parentNode, config, input.nextSibling);
        newInput.value = input.value.slice(cursorPosition);
        if (newInput.value.length > 0) {
            // we only set the name of inputs that contain something.
            // this way the form won't contain empty values.
            newInput.name = config.name;
        }
        input.value = input.value.slice(0, cursorPosition);
        if (input.value.length === 0) {
            // see above
            input.removeAttribute("name");
        }
        input.selectionStart = 0;
        return cursorPosition > 0;
    }

    function focusNextInput(input) {
        // we might use "nextChild" here, but it turns out to be
        // a little dangerous to assume no stray elements between
        // the inputs...
        var inputs = input.parentNode.querySelectorAll("input");
        for (var i = 0; i < inputs.length - 1; i++) {
            if (inputs[i] === input) {
                var next = inputs[i+1];
                next.focus();
                next.selectionStart = next.selectionEnd = 0;
                break;
            }
        }
    }

    function focusPrevInput(input) {
        var inputs = input.parentNode.querySelectorAll("input");
        for (var i = 1; i < inputs.length; i++) {
            if (inputs[i] === input) {
                var prev = inputs[i-1];
                prev.focus();
                prev.selectionStart = prev.selectionEnd = prev.value.length;
                break;
            }
        }
    }

    function removeIfEmpty(input) {
        if (input.parentNode.querySelectorAll("input").length > 1 &&
            input.value == "") {
            focusNextInput(input);
            input.parentNode && input.parentNode.removeChild(input);            
        }
    }
        
    function addInput(container, config, before) {
        var newInput = document.createElement("input");
        newInput.classList = "author";
        newInput.type = "text";
        newInput.placeholder = config.placeholder;
        newInput.classList.add.apply(newInput.classList, config.classes)
        if (before) {
            container.insertBefore(newInput, before);
        } else {
            container.appendChild(newInput);
        }
        autosizeInput(newInput);
        return newInput;
    }
    
    function onInput (event) {
        if (event.target.parentNode == this.container) {
            var inputs = this.container.querySelectorAll("input");
            var lastInput = inputs[inputs.length - 1];
            for (var input of inputs) {
                if (input == event.target && input == lastInput) {
                    if (input.value) {
                        addInput(this.container, this.config);
                    }
                }
            }
        }
    }

    function onBlur (event) {
        if (event.target.parentNode == this.container) {
            var inputs = this.container.querySelectorAll("input");
            var index = Array.prototype.slice.call(inputs).indexOf(event.target);
            if (!event.target.value && index != inputs.length - 1) {
                this.container.removeChild(event.target);
            }
        }
    }

    // Thanks to http://stackoverflow.com/a/7168967/229599
    // TODO: this is *heavy*
    function autosizeInput(input) {
        
        var min = 100, max = 300, pad_right = 5;

        input.style.width = min+'px';
        input.onkeypress = input.onkeydown = input.onkeyup = function(){
            var input = this;
            setTimeout(function(){
                var tmp = document.createElement('div');
                tmp.style.padding = '0';
                if(getComputedStyle)
                    tmp.style.cssText = getComputedStyle(input, null).cssText;
                if(input.currentStyle)
                    tmp.style.cssText = input.currentStyle.cssText;
                tmp.style.width = '';
                tmp.style.position = 'absolute';
                tmp.innerHTML = input.value
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;")
                    .replace(/ /g, '&nbsp;');
                input.parentNode.appendChild(tmp);
                var width = tmp.clientWidth+pad_right+1;
                tmp.parentNode.removeChild(tmp);
                if(min <= width && width <= max)
                    input.style.width = width+'px';
            }, 1);
        }
    }
    
    return Montag;
    
})()
