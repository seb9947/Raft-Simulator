import asyncio
import sys
from typing import List, Tuple
from nodes.raft_node import RaftNode

async def main() -> None:
    """
    Entry point for starting a Raft node from command line arguments.
    Expects arguments: <node_id> <host> <port> <peer1_id:peer1_host:peer1_port> ...
    """
    if len(sys.argv) < 4:
        print("Usage: python main.py <node_id> <host> <port> <peer1_id:peer1_host:peer1_port> ...")
        return

    node_id: str = sys.argv[1]
    host: str = sys.argv[2]
    port: int = int(sys.argv[3])
    peer_strings: List[str] = sys.argv[4:]

    peers: List[Tuple[str, str, int]] = []
    for peer_str in peer_strings:
        peer_id, peer_host, peer_port = peer_str.split(":")
        peers.append((peer_id, peer_host, int(peer_port)))

    node = RaftNode(node_id=node_id, host=host, port=port, peers=peers)
    await node.start()

    print(f"Node {node_id} started on {host}:{port} with peers: {peers}")

    # Keep the node running forever
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print(f"Shutting down node {node_id}")
        await node.stop()

if __name__ == "__main__":
    asyncio.run(main())