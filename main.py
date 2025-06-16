import asyncio
import sys
from nodes.raft_node import RaftNode

async def main():
    if len(sys.argv) < 4:
        print("Usage: python main.py <node_id> <port> <peer1:port1> <peer2:port2> ...")
        return

    node_id = sys.argv[1]
    host = sys.argv[2]
    port = int(sys.argv[3])
    peer_strings = sys.argv[4:]

    peers = []
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
        await node.stop()  # If you have implemented graceful shutdown

if __name__ == "__main__":
    asyncio.run(main())