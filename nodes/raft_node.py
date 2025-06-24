import asyncio
import random
import time
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from nodes.raft_server import RaftServerProtocol, send_to_peer


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


class NodeState(Enum):
    """Enumeration of Raft node states."""
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()


class LogEntry:
    """
    Represents a single log entry in the Raft log.
    """
    def __init__(self, term: int, command: str) -> None:
        self.term: int = term
        self.command: str = command

    def __repr__(self) -> str:
        return f"LogEntry(term={self.term}, command={self.command})"


class RaftNode:
    """
    Represents a Raft node, handling state, log, and protocol logic.
    """
    def __init__(
        self,
        node_id: str,
        peers: List[Tuple[str, str, int]],
        host: str,
        port: int
    ) -> None:
        self.node_id: str = node_id
        self.peers: List[Tuple[str, str, int]] = peers  # List of (peer_id, host, port)
        self.host: str = host
        self.port: int = port

        self.log: List[LogEntry] = []
        self.commit_index: int = -1
        self.last_applied: int = -1
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        self.state: NodeState = NodeState.FOLLOWER
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        self.votes_received: int = 0

        self.reset_election_timeout()
        self.heartbeat_interval: float = 1.0
        self.last_heartbeat: float = time.time()
        self.running: bool = True

    def majority(self) -> int:
        """
        Calculate the majority count for the current cluster.
        """
        return (len(self.peers) + 1) // 2 + 1

    def reset_election_timeout(self) -> None:
        """
        Reset the election timeout to a new random value.
        """
        self.election_timeout: float = random.uniform(4.0, 6.0)

    async def start(self) -> None:
        """
        Start the Raft node's server and main event loop.
        """
        loop = asyncio.get_running_loop()
        self.server = await loop.create_server(
            lambda: RaftServerProtocol(self),
            self.host,
            self.port
        )
        print(f"Node {self.node_id} listening on {self.host}:{self.port}")

        await asyncio.sleep(1.0)  # Allow other nodes to start

        while self.running:
            now = time.time()

            if self.state != NodeState.LEADER and now - self.last_heartbeat > self.election_timeout:
                await self.start_election()

            elif self.state == NodeState.LEADER and now - self.last_heartbeat >= self.heartbeat_interval:
                await self.send_heartbeats()

            if self.state == NodeState.LEADER and random.random() < 0.01:
                await self.append_client_command(f"SET x = {random.randint(1, 100)}")

            if self.commit_index > self.last_applied:
                self.apply_committed_entries()

            await asyncio.sleep(0.1)

    def apply_committed_entries(self) -> None:
        """
        Apply all committed log entries to the state machine.
        """
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            print(f"Node {self.node_id} applied: {entry.command}")

    async def start_election(self) -> None:
        """
        Start a new election for leadership.
        """
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = 1
        self.last_heartbeat = time.time()
        self.reset_election_timeout()

        print(f"Node {self.node_id} starting election for term {self.current_term}")

        for peer_id, host, port in self.peers:
            msg = Message(
                MessageType.REQUEST_VOTE, self.node_id, peer_id, self.current_term,
                data={'candidate_id': self.node_id}
            )
            await send_to_peer(host, port, msg.to_dict())

    async def handle_message(self, message_dict: Dict[str, Any]) -> None:
        """
        Handle an incoming Raft protocol message.
        """
        message = Message.from_dict(message_dict)

        if message.term > self.current_term:
            prev_state = self.state
            self.current_term = message.term
            self.state = NodeState.FOLLOWER
            self.voted_for = None
            if prev_state == NodeState.LEADER:
                print(f"Node {self.node_id} demoted from leader")

        if message.type == MessageType.REQUEST_VOTE:
            if self.voted_for is None or self.voted_for == message.data['candidate_id']:
                self.voted_for = message.data['candidate_id']
                peer_id, peer_host, peer_port = self._get_peer(message.src)
                response = Message(
                    MessageType.VOTE_RESPONSE, self.node_id, message.src, self.current_term,
                    data={'vote_granted': True}
                )
                await send_to_peer(peer_host, peer_port, response.to_dict())

        elif message.type == MessageType.VOTE_RESPONSE:
            if self.state == NodeState.CANDIDATE and message.term == self.current_term:
                if message.data.get('vote_granted'):
                    self.votes_received += 1
                    if self.votes_received >= self.majority():
                        await self.become_leader()

        elif message.type == MessageType.APPEND_ENTRIES:
            if self.state != NodeState.LEADER:
                self.last_heartbeat = time.time()

            entries = message.data.get('entries', [])
            if entries:
                for entry_dict in entries:
                    entry = LogEntry(**entry_dict)
                    self.log.append(entry)
                print(f"Node {self.node_id} appended entries: {entries}")

            leader_commit = message.data.get('leader_commit', -1)
            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, len(self.log) - 1)

            self.apply_committed_entries()

            ack_index = len(self.log) - 1
            peer_id, peer_host, peer_port = self._get_peer(message.src)
            response = Message(
                MessageType.APPEND_RESPONSE, self.node_id, message.src, self.current_term,
                data={'ack_index': ack_index}
            )
            await send_to_peer(peer_host, peer_port, response.to_dict())

        elif message.type == MessageType.APPEND_RESPONSE:
            if self.state == NodeState.LEADER:
                follower = message.src
                ack_index = message.data.get('ack_index', -1)
                self.match_index[follower] = ack_index
                self.next_index[follower] = ack_index + 1

                replicated_count = sum(
                    1 for idx in self.match_index.values() if idx >= ack_index
                ) + 1

                if replicated_count >= self.majority() and ack_index > self.commit_index:
                    self.commit_index = ack_index
                    print(f"Leader {self.node_id} committed index {ack_index}: {self.log[ack_index]}")

    async def append_client_command(self, command: str) -> None:
        """
        Append a client command to the log (leader only).
        """
        if self.state != NodeState.LEADER:
            print(f"Node {self.node_id} rejected client command — not leader.")
            return

        entry = LogEntry(term=self.current_term, command=command)
        self.log.append(entry)
        print(f"Leader {self.node_id} appended {entry} to log")

        for peer_id, host, port in self.peers:
            msg = Message(
                MessageType.APPEND_ENTRIES,
                self.node_id,
                peer_id,
                self.current_term,
                data={
                    'entries': [entry.__dict__],
                    'leader_commit': self.commit_index
                }
            )
            await send_to_peer(host, port, msg.to_dict())

    async def become_leader(self) -> None:
        """
        Transition this node to the leader state.
        """
        self.state = NodeState.LEADER
        print(f"Node {self.node_id} became leader for term {self.current_term}")
        last_log_index = len(self.log) - 1
        for peer_id, _, _ in self.peers:
            self.next_index[peer_id] = last_log_index + 1
            self.match_index[peer_id] = -1
        await self.send_heartbeats()

    async def send_heartbeats(self) -> None:
        """
        Send heartbeat (empty AppendEntries) messages to all peers.
        """
        for peer_id, host, port in self.peers:
            if random.random() < 0.02:
                await asyncio.sleep(5)

            print(f"Leader {self.node_id} sending heartbeat to {peer_id}")
            msg = Message(
                MessageType.APPEND_ENTRIES,
                self.node_id,
                peer_id,
                self.current_term,
                data={'entries': [], 'leader_commit': self.commit_index}
            )
            await send_to_peer(host, port, msg.to_dict())
        self.last_heartbeat = time.time()

    def _get_peer(self, peer_id: str) -> Tuple[str, str, int]:
        """
        Retrieve peer information by peer ID.

        Args:
            peer_id: The ID of the peer.

        Returns:
            Tuple containing (peer_id, host, port).

        Raises:
            ValueError: If the peer is not found.
        """
        for peer in self.peers:
            if peer[0] == peer_id:
                return peer
        raise ValueError(f"Peer {peer_id} not found")