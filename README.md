# Raft Consensus Algorithm Simulator (Python)

This project is a simulation of the [Raft consensus algorithm](https://raft.github.io/), implemented entirely in Python, for educational purposes. It demonstrates how Raft achieves **distributed consensus** through leader election, log replication, and commitment of commands to a replicated state machine.

The simulation runs in a single process with virtual nodes communicating via TCP using asyncio, but maintains the logic and structure of a real distributed system.

---

## Project Structure
```
Raft-Simulator/
│
├── main.py                # Entry point: starts the simulation
│
├── simulation/
│ ├── simulation_runner.py # Manages simulation ticks, starts nodes
│ └── message_bus.py       # In-memory message passing between nodes
│
├── nodes/
│ ├── raft_node.py         # Core Raft node logic (leader election, log replication)
│ └── raft_server.py       # Asyncio TCP server/client communication utilities
│
├── main.py                # Launches a single Raft Node 
└── launch_all_nodes.py    # Coordinates running of multiple nodes

```

---

---

## How It Works

### Simulation Flow

1. `main.py` starts one or more Raft nodes, each listening on a unique TCP port.
2. Each node runs asynchronously, managing timers for election timeouts and heartbeats.
3. Nodes communicate via TCP connections using JSON-encoded messages terminated by newlines.
4. Messages use a custom Message class with explicit JSON serialization/deserialization that converts enum types to strings for compatibility.
5. Once a leader is elected:
   - It periodically sends `AppendEntries` messages (including heartbeats) to followers.
   - It can accept new commands (e.g. `"SET x = 1"`, currently randomly generated in the leader - this could be expanded in the future to accept client input, see [Future Work](#future-work)) and appends them to its local log.
   - The leader sends the new log entries to followers via `AppendEntries`.
   - When a **majority of nodes** acknowledge replication of an entry, the leader **commits** it.
   - The leader includes the `commit_index` in future `AppendEntries`, prompting followers to apply the entry to their state machines.
   - All committed entries are applied in order, ensuring consistency across the cluster.

---

## Raft Algorithm Phases

### 1. Leader Election
- Each node starts as a **Follower**.
- If a node does **not hear from a leader** within a randomized timeout (e.g. 4–6 seconds), it becomes a **Candidate**.
- Candidates increment their term, vote for themselves, and request votes from other nodes.
- A node becomes **Leader** if it receives a **majority** of votes.

### 2. Log Replication
- Leaders accept new client commands (simulated) and append them to their local log.
- They replicate these entries to followers via `AppendEntries` messages.
- Once a **majority of nodes** have stored the entry, the leader **commits** it.

### 3. Committing and Applying
- The leader and all followers **apply committed entries** to their state machine.
- The current system just logs this to the console, but it could be extended to track actual state.

---

## Networking and Message Handling

Nodes listen on TCP sockets and accept connections from peers.

Messages are JSON-encoded and newline-delimited.

Custom serialization converts enum fields in messages to strings for JSON compatibility.

The raft_server.py module implements an asyncio Protocol for incoming connections and a send_to_peer coroutine for outbound messages.

---

## Simulated Behavior

- **Election timeouts** are randomized to avoid split votes.
- **Heartbeats** are sent periodically by the leader to maintain authority and advance commits.
- **Log entries** are commands like `"SET x = 42"`, simulated by the leader.
- **Message delays or losses** are not simulated, but could be added to test resilience.

---

## Running the Simulation

To launch with a set number of nodes simultaneously, use:
```bash
python launch_all_nodes.py
```

Else, you can also run individual nodes using `main.py`. 

---

## Future Work

- Clean up code, add type hints, refactor messy classes.
- Accept real client commands interactively.
- Simulate network partitions, delays, and message loss.
- Implement persistent log and node state.
- Add advanced Raft features like pre-vote and log consistency checks.


---

## Resources

- [Designing Data-Intensive Applications — Martin Kleppmann](https://dataintensive.net)
- [The Raft Paper (2014)](https://raft.github.io/raft.pdf)
- [Raft Visualization Tool](https://raft.github.io/)

---

## Author

This project was built to explore the internals of distributed consensus, and to put into practice concepts from *Designing Data-Intensive Applications* by Martin Kleppmann.
