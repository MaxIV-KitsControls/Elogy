"""
Perform configured actions when various things happen.
Actions themselves are presumably defined in the config file.
"""

from functools import partial
import logging
from threading import Thread

from flask import current_app
from blinker import Namespace


signals = Namespace()

# these are the signals currently defined. They should be sent from the
# code whenever the relevant things have happened.
new_entry = signals.signal("new_entry")
edit_entry = signals.signal("edit_entry")
new_logbook = signals.signal("new_logbook")
edit_logbook = signals.signal("edit_logbook")


def on_signal(signal_name, *args, **kwargs):
    "Find and run any action configured for the signal."
    action_config = current_app.config.get("ACTIONS", {})
    action = action_config.get(signal_name)
    if action:
        logging.debug("Running configured action for '%s'", signal_name)
        try:
            # The action is run in a thread, to prevent it from hanging
            # the whole app, e.g. if it does some slow network stuff.
            # This is a bit naive, a flood of actions might create a
            # ridiculous number of threads. Maybe better to use a worker
            # pool and a queue or something?
            Thread(target=action, args=args, kwargs=kwargs).run()
        except Exception as e:
            logging.error("Caught exception in action for '%s': %s",
                          signal_name, e)


for name, signal in signals.items():
    signal.connect(partial(on_signal, name), weak=False)
