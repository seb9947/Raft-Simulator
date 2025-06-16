import os
import subprocess
import sys
import time

NODES = [
    ("A", 9001),
    ("B", 9002),
    ("C", 9003),
    ("D", 9004),
    ("E", 9005),
]

HOST = "127.0.0.1"
LOG_DIR = "logs"

def build_peer_list(node_id, nodes):
    return [f"{nid}:{HOST}:{port}" for nid, port in nodes if nid != node_id]

def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    processes = []
    for node_id, port in NODES:
        peer_args = build_peer_list(node_id, NODES)
        cmd = [
            sys.executable, "main.py", node_id, HOST, str(port), *peer_args
        ]
        log_path = os.path.join(LOG_DIR, f"{node_id}.log")
        log_file = open(log_path, "w") # Switch to w to overwrite
        
        print(f"Starting Node {node_id} on port {port} (logging to {log_path})...")
        proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        processes.append((proc, log_file))
        time.sleep(0.5)  # slight delay to stagger startup

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
