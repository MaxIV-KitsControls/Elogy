window.Montag = (function () {

    function Montag(element, config) {
        this.container = element;
        this.form = element.form;
        this.config = config;

        this.container.addEventListener("keypress", function (event) {
            window.setTimeout(
                // TODO: some proper throttling here plz
                function () {checkInputs(element, config)}, 10);
        });

        checkInputs(this.container, config);
    }

    function checkInputs(container, config) {
        var inputs = Array.prototype.slice.call(
            container.querySelectorAll("input"));
        for(var i=0; i<inputs.length-1; i++) {
            if (inputs[i].value == "") {
                container.removeChild(inputs[i]);
                inputs[i+1].focus();
            }
        }
        if (inputs.length === 0 || inputs[inputs.length-1].value != "") {
            var extraInput = document.createElement("input");
            extraInput.name = config.name;
            extraInput.classList.add.apply(extraInput.classList, config.classes);
            extraInput.placeholder = config.placeholder;
            container.appendChild(extraInput);
        }
    }

    return Montag;
    
})();
