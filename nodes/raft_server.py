import asyncio
import json
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .raft_node import RaftNode

class RaftServerProtocol(asyncio.Protocol):
    """
    Asyncio Protocol implementation for a Raft server node.
    Handles incoming connections and message parsing.
    """
    def __init__(self, node: 'RaftNode') -> None:
        """
        Initialize the protocol with a reference to the node.

        Args:
            node: The Raft node instance that will handle messages.
        """
        self.node = node
        self.buffer: bytes = b""

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """
        Called when a connection is made.

        Args:
            transport: The transport representing the connection.
        """
        self.transport = transport

    def data_received(self, data: bytes) -> None:
        """
        Called when data is received from the connection.

        Args:
            data: The bytes received from the connection.
        """
        self.buffer += data
        while b"\n" in self.buffer:
            msg, self.buffer = self.buffer.split(b"\n", 1)
            message = json.loads(msg.decode())
            asyncio.create_task(self.node.handle_message(message))

    def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the connected peer.

        Args:
            message: The message dictionary to send.
        """
        msg = json.dumps(message).encode() + b"\n"
        self.transport.write(msg)


async def send_to_peer(host: str, port: int, message: Dict[str, Any]) -> None:
    """
    Send a message to a peer node over TCP.

    Args:
        host: The hostname or IP address of the peer.
        port: The port number of the peer.
        message: The message dictionary to send.
    """
    reader, writer = await asyncio.open_connection(host, port)
    msg = json.dumps(message).encode() + b"\n"
    writer.write(msg)
    await writer.drain()
    writer.close()
    await writer.wait_closed()
