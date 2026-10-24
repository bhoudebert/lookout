"""Run an action every so often on a background thread (openspec: scheduling)."""

import threading
from collections.abc import Callable


class Periodic:
    """Calls ``action`` every ``interval_seconds`` until stopped. The first call comes after one interval."""

    def __init__(self, interval_seconds: float, action: Callable[[], object]) -> None:
        self._interval = interval_seconds
        self._action = action
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="lookout-schedule")

    def start(self) -> None:
        """Begin ticking."""
        self._thread.start()

    def stop(self) -> None:
        """Stop ticking and wait for the thread."""
        self._stop.set()
        self._thread.join()

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            self._action()
