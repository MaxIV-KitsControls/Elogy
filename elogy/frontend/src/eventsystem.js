/* 
   A very simple eventbus that can be used to distribute messages
   in a 'one-to-many' way.

   A listener can subscribe a callback to any topic (identified by
   an arbitrary string). The callback will be run whenever an
   event is published on that topic.

   Publishers can also include any data with their events.
 */

class EventBus {

    constructor () {
        this.store = {};
    }

    subscribe (topic, callback) {
        if (this.store[topic]) {
            this.store[topic].push(callback);
        } else {
            this.store[topic] = [callback];
        }
    }

    unsubscribe (topic, callback) {
        if (this.store[topic]) {
            const callbacks = this.store[topic];
            const index = callbacks.indexOf(callback);
            if (index != -1) {
                this.store[topic] = this.store[topic].splice(index, 1);
            }
        }        
    }
    
    publish (topic, data) {
        const callbacks = this.store[topic] || []; 
        callbacks.forEach(callback => callback(data));
        return callbacks.length > 0;        
    }
}


export default EventBus;
