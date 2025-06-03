from collections import deque
from enum import Enum, auto

class MessageType(Enum):
    REQUEST_VOTE = auto()
    VOTE_RESPONSE = auto()
    APPEND_ENTRIES = auto()
    APPEND_RESPONSE = auto()

class Message:
    def __init__(self, type_, src, dst, term, data=None):
        self.type = type_
        self.src = src
        self.dst = dst
        self.term = term
        self.data = data or {}

class MessageBus:
    def __init__(self):
        self.queues = {}

    def register(self, node_id):
        self.queues[node_id] = deque()

    def send(self, message):
        if message.dst in self.queues:
            self.queues[message.dst].append(message)

    def receive(self, node_id):
        if self.queues[node_id]:
            return self.queues[node_id].popleft()
        return None
