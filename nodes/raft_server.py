import asyncio
import json

class RaftServerProtocol(asyncio.Protocol):
    def __init__(self, node):
        self.node = node
        self.buffer = b""

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.buffer += data
        while b"\n" in self.buffer:
            msg, self.buffer = self.buffer.split(b"\n", 1)
            message = json.loads(msg.decode())
            asyncio.create_task(self.node.handle_message(message))

    def send_message(self, message):
        msg = json.dumps(message).encode() + b"\n"
        self.transport.write(msg)


async def send_to_peer(host, port, message):
    reader, writer = await asyncio.open_connection(host, port)
    msg = json.dumps(message).encode() + b"\n"
    writer.write(msg)
    await writer.drain()
    writer.close()
    await writer.wait_closed()
