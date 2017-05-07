const EventSystem = (function() {

    const store = {};

    return {
        publish: function (event, data) {
            const callbacks = store[event] || []; 
            callbacks.forEach(callback => callback(data));
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
