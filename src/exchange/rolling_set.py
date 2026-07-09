from collections import deque

class RollingSet:
    def __init__(self, maxsize: int = 1000):
        self._set: set = set()
        self._queue: deque = deque()
        self._maxsize = maxsize

    def add(self, item) -> None:
        if item in self._set:
            return
        if len(self._queue) >= self._maxsize:
            oldest = self._queue.popleft()
            self._set.discard(oldest)
        self._queue.append(item)
        self._set.add(item)

    def __contains__(self, item) -> bool:
        return item in self._set