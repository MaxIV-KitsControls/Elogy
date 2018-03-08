from functools import wraps


def send_signal(signal):
    """Decorator that ensures that the given signal is sent
    with the result of the decorated view function, if it's
    successful."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            signal.send(result)
            return result
        return decorated_function
    return decorator
