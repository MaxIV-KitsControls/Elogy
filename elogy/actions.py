"""
Perform configured actions when various things happen.
"""

from functools import partial
from threading import Thread

from blinker import Namespace


signals = Namespace()

new_entry = signals.signal("new_entry")
edit_entry = signals.signal("edit_entry")
new_logbook = signals.signal("new_logbook")
edit_logbook = signals.signal("edit_logbook")


def on_signal(signal_name, app, *args, **kwargs):
    "Find and run any relevant action configured for the signal."
    action_config = app.config.get("ACTIONS", {})
    action = action_config.get(signal_name)
    if action:
        try:
            Thread(target=action, args=args, kwargs=kwargs).run()
        except Exception as e:
            print("Caught exception in action:", e)


for name, signal in signals.items():
    signal.connect(partial(on_signal, name), weak=False)
