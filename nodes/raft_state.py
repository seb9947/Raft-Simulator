from enum import Enum, auto


class NodeState(Enum):
    """Enumeration of Raft node states."""
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()