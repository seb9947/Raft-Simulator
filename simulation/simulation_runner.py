import time
from nodes.raft_node import RaftNode
from nodes.message_bus import MessageBus

def run_simulation():
    node_ids = ['A', 'B', 'C', 'D', 'E']
    bus = MessageBus()
    nodes = [RaftNode(node_id, [pid for pid in node_ids if pid != node_id], bus) for node_id in node_ids]

    for node in nodes:
        node.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for node in nodes:
            node.running = False
        for node in nodes:
            node.join()
