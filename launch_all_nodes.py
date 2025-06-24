import os
import subprocess
import sys
import time
from typing import List, Tuple
from io import TextIOWrapper

NODES: List[Tuple[str, int]] = [
    ("A", 9001),
    ("B", 9002),
    ("C", 9003),
    ("D", 9004),
    ("E", 9005),
]

HOST: str = "127.0.0.1"
LOG_DIR: str = "logs"


def build_peer_list(node_id: str, nodes: List[Tuple[str, int]]) -> List[str]:
    """
    Build a list of peer node addresses excluding the given node_id.

    Args:
        node_id: The ID of the current node.
        nodes: List of tuples containing node IDs and their ports.

    Returns:
        List of peer addresses in the format 'ID:HOST:PORT'.
    """
    return [f"{nid}:{HOST}:{port}" for nid, port in nodes if nid != node_id]


def main() -> None:
    """
    Launch all Raft nodes as subprocesses, each with its own log file.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    processes: List[Tuple[subprocess.Popen, TextIOWrapper]] = []

    for node_id, port in NODES:
        peer_args = build_peer_list(node_id, NODES)
        cmd = [
            sys.executable, "main.py", node_id, HOST, str(port), *peer_args
        ]
        log_path = os.path.join(LOG_DIR, f"{node_id}.log")
        log_file = open(log_path, "w")

        print(f"Starting Node {node_id} on port {port} (logging to {log_path})...")
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        processes.append((proc, log_file))
        time.sleep(0.5)  # Slight delay to stagger startup

    print("All nodes started. Logs are in the 'logs/' directory. Press Ctrl+C to stop.")

    try:
        for proc, _ in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down all nodes...")
        for proc, log_file in processes:
            proc.terminate()
            log_file.close()


if __name__ == "__main__":
    main()
