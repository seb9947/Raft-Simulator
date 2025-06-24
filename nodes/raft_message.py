from enum import Enum, auto
from typing import Any, Dict, Optional


class MessageType(Enum):
    """Enumeration of Raft message types."""
    REQUEST_VOTE = auto()
    VOTE_RESPONSE = auto()
    APPEND_ENTRIES = auto()
    APPEND_RESPONSE = auto()


class Message:
    """
    Represents a Raft protocol message.
    """
    def __init__(
        self,
        type_: MessageType,
        src: str,
        dst: str,
        term: int,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        self.type: MessageType = type_
        self.src: str = src
        self.dst: str = dst
        self.term: int = term
        self.data: Dict[str, Any] = data or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary for serialization.
        """
        return {
            "type": self.type.name,
            "src": self.src,
            "dst": self.dst,
            "term": self.term,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Message":
        """
        Create a Message instance from a dictionary.
        """
        return cls(
            type_=MessageType[d["type"]],
            src=d["src"],
            dst=d["dst"],
            term=d["term"],
            data=d.get("data", {}),
        )