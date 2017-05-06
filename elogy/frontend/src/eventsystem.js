const EventSystem = (function() {

    const store = {};

    return {
        publish: function (event, data) {
            var queue = store[event];

            if (typeof queue === 'undefined') {
                return false;
            }

            while(queue.length > 0) {
                (queue.shift())(data);
            }

            return true;
        },
        subscribe: function(event, callback) {
            if (typeof store[event] === 'undefined') {
                store[event] = [];
            }

            store[event].push(callback);
        },
        unsubscribe: function(event, callback) {
            if (event in store) {
                const callbacks = store[event];
                const index = callbacks.indexOf(callback);
                store[event] = store[event].splice(index, 1);
            }
        }
    };
}());


export default EventSystem;
