"""Small in-process worker pools so one slow user's work never blocks everyone else.

The scheduler tick only dispatches; each unit of work runs on its own thread and owns
its per-user advisory lock. Keys already in flight in this process are not resubmitted,
and the database lock still prevents two processes from running the same user's work.
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor


class WorkPool:
    def __init__(self, name: str, workers: int):
        self._executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix=name)
        self._inflight: set = set()
        self._lock = threading.Lock()
        self._log = logging.getLogger(f'{__name__}.{name}')

    def submit(self, key, fn, *args) -> bool:
        with self._lock:
            if key in self._inflight:
                return False
            self._inflight.add(key)

        def run():
            try:
                fn(*args)
            except Exception:
                self._log.exception('Work item %s failed', key)
            finally:
                with self._lock:
                    self._inflight.discard(key)

        try:
            self._executor.submit(run)
        except RuntimeError:  # Executor shut down during application exit.
            with self._lock:
                self._inflight.discard(key)
            return False
        return True

    def busy(self, key) -> bool:
        with self._lock:
            return key in self._inflight

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)
