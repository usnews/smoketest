import threading

from smoketest.utils import chunkify


def get_threads_and_stop_event(directives, n_threads):
    stop_event = threading.Event()
    threads = []
    for chunk in chunkify(directives, n_threads):
        thread = threading.Thread(target=_get_runner(chunk, stop_event))
        threads.append(thread)
    return threads, stop_event


def _get_runner(directives, stop_event):
    """Return a function that runs all the directives in the given list until
    the stop event is set.
    """
    def runner():
        for directive in directives:
            if not stop_event.is_set():
                directive.run()
            else:
                break
    return runner
