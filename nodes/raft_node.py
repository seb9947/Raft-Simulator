from enum import Enum, auto
import time
import random
import threading
from nodes.message_bus import Message, MessageType

class NodeState(Enum):
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()

class LogEntry:
    def __init__(self, term, command):
        self.term = term
        self.command = command

    def __repr__(self):
        return f"LogEntry(term={self.term}, command={self.command})"


class RaftNode(threading.Thread):
    def __init__(self, node_id, peers, message_bus):
        super().__init__()
        self.log = []  # List[LogEntry]
        self.commit_index = -1
        self.last_applied = -1
        self.next_index = {}     # For each peer: next log index to send
        self.match_index = {}    # For each peer: highest index known to be replicated

        self.node_id = node_id
        self.peers = peers
        self.message_bus = message_bus

        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for = None
        self.votes_received = 0

        self.reset_election_timeout()
        self.heartbeat_interval = 1.0  # Leader heartbeat every second
        self.last_heartbeat = time.time()

        self.running = True
        self.message_bus.register(self.node_id)


    def majority(self):
        return (len(self.peers) + 1) // 2 + 1
    

    def reset_election_timeout(self):
        self.election_timeout = random.uniform(4.0, 6.0)


    def run(self):
        while self.running:
            now = time.time()

            if self.state != NodeState.LEADER and now - self.last_heartbeat > self.election_timeout:
                self.start_election()

            elif self.state == NodeState.LEADER and now - self.last_heartbeat >= self.heartbeat_interval:
                self.send_heartbeats()

            message = self.message_bus.receive(self.node_id)
            if message:
                self.handle_message(message)

            if self.state == NodeState.LEADER and random.random() < 0.01:
                self.append_client_command(f"SET x = {random.randint(1,100)}")

            if self.commit_index > self.last_applied:
                self.apply_committed_entries()

            time.sleep(0.1)

    
    def apply_committed_entries(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            print(f"Node {self.node_id} applied: {entry.command}")


    def start_election(self):
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = 1
        self.last_heartbeat = time.time()

        # Reset the election timeout each time you run an election
        self.reset_election_timeout()

        print(f"Node {self.node_id} starting election for term {self.current_term}")

        for peer in self.peers:
            msg = Message(
                MessageType.REQUEST_VOTE, self.node_id, peer, self.current_term,
                data={'candidate_id': self.node_id}
            )
            self.message_bus.send(msg)

    def handle_message(self, message):
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
                self.message_bus.send(Message(
                    MessageType.VOTE_RESPONSE, self.node_id, message.src, self.current_term,
                    data={'vote_granted': True}
                ))

        elif message.type == MessageType.VOTE_RESPONSE:
            if self.state == NodeState.CANDIDATE and message.term == self.current_term:
                if message.data.get('vote_granted'):
                    self.votes_received += 1
                    if self.votes_received > len(self.peers) // 2:
                        self.become_leader()

        elif message.type == MessageType.APPEND_ENTRIES:
            if self.state != NodeState.LEADER:
                self.last_heartbeat = time.time()

            entries = message.data.get('entries', [])
            if entries:
                for entry in entries:
                    self.log.append(entry)
                print(f"Node {self.node_id} appended entries: {entries}")

            leader_commit = message.data.get('leader_commit', -1)
            if leader_commit > self.commit_index:
                self.commit_index = min(leader_commit, len(self.log) - 1)

            # Apply any committed entries
            self.apply_committed_entries()

            # Respond back to the leader
            ack_index = len(self.log) - 1
            self.message_bus.send(Message(
                MessageType.APPEND_RESPONSE,
                self.node_id,
                message.src,
                self.current_term,
                data={'ack_index': ack_index},
            ))

        elif message.type == MessageType.APPEND_RESPONSE:
            if self.state == NodeState.LEADER:
                follower = message.src
                ack_index = message.data.get('ack_index', -1)

                self.match_index[follower] = ack_index
                self.next_index[follower] = ack_index + 1

                # Count how many nodes (including self) have replicated this index
                replicated_count = sum(
                    1 for idx in self.match_index.values() if idx >= ack_index
                ) + 1  # +1 for leader

                if replicated_count >= self.majority() and ack_index > self.commit_index:
                    self.commit_index = ack_index
                    print(f"Leader {self.node_id} committed index {ack_index}: {self.log[ack_index]}")


    def append_client_command(self, command):
        if self.state != NodeState.LEADER:
            print(f"Node {self.node_id} rejected client command — not leader.")
            return

        entry = LogEntry(term=self.current_term, command=command)
        self.log.append(entry)
        print(f"Leader {self.node_id} appended {entry} to log")

        # Send it to followers
        for peer in self.peers:
            msg = Message(
                MessageType.APPEND_ENTRIES,
                self.node_id,
                peer,
                self.current_term,
                data={
                    'entries': [entry],
                    'leader_commit': self.commit_index,
                },
            )
            self.message_bus.send(msg)



    def become_leader(self):
        self.state = NodeState.LEADER
        print(f"Node {self.node_id} became leader for term {self.current_term}")
        if self.state == NodeState.LEADER:
            last_log_index = len(self.log) - 1
            for peer in self.peers:
                self.next_index[peer] = last_log_index + 1
                self.match_index[peer] = -1

        self.send_heartbeats()


    def send_heartbeats(self):
        for peer in self.peers:
            # simulate random delays
            if random.random() < 0.02:
                time.sleep(5)

            print(f"Leader {self.node_id} sending heartbeat to {peer}")
            msg = Message(
                MessageType.APPEND_ENTRIES,
                self.node_id,
                peer,
                self.current_term,
                data={
                    'entries': [],
                    'leader_commit': self.commit_index,
                }
            )
            self.message_bus.send(msg)
        self.last_heartbeat = time.time()