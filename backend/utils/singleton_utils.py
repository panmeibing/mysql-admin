from threading import Lock


def singleton(cls):
    instance = {}
    instance_lock = Lock()

    def wrapper(*args, **kwargs):
        if cls not in instance:
            with instance_lock:
                instance[cls] = cls(*args, **kwargs)
        return instance[cls]

    return wrapper
