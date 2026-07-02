from multiprocessing import Queue
from queue import Empty

from messages import Message

class EventBus:
    def __init__(self, send_qs: dict[str, Queue], rcv_q: Queue):
        self._send_qs = send_qs
        self._rcv_q = rcv_q
    
    def subscribe(self, callback) -> None:
        while True: 
            try:
                msg = self._rcv_q.get(timeout=0.1) 
                callback(msg)
            except Empty:
                continue

    def send(self, client_id: str, message: Message) -> None:
        self._send_qs[client_id].put(message)

    def publish(self, message: Message) -> None:
        for q in self._send_qs.values():
            q.put(message)