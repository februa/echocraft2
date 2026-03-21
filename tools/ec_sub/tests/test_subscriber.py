"""Tests for ec-sub subscriber domain class."""

import io
import socket
import struct
import threading

import pytest

from ec_sub.subscriber import Subscriber

# Protocol constants (must match publisher/subscriber)
_MSG_BLOCK = 1
_MSG_EOF = 0
_MSG_FORMAT = "!B"
_HEADER_FORMAT = "!I"


def _mock_publisher(port_holder: list, n_clients: int, blocks: list[bytes]):
    """Run a mock publisher that sends blocks to connected clients.

    Args:
        port_holder: List to store the bound port (for synchronization).
        n_clients: Number of clients to accept.
        blocks: List of block payloads to send.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(n_clients)
    port_holder.append(server.getsockname()[1])

    clients = []
    for _ in range(n_clients):
        conn, _ = server.accept()
        clients.append(conn)

    for block in blocks:
        frame = (
            struct.pack(_MSG_FORMAT, _MSG_BLOCK)
            + struct.pack(_HEADER_FORMAT, len(block))
            + block
        )
        for conn in clients:
            conn.sendall(frame)

    eof = struct.pack(_MSG_FORMAT, _MSG_EOF)
    for conn in clients:
        conn.sendall(eof)
        conn.close()

    server.close()


class TestSubscriber:
    """Tests for Subscriber domain class."""

    def test_receive_before_connect_raises(self):
        sub = Subscriber()
        with pytest.raises(RuntimeError, match="Not connected"):
            sub.receive(io.BytesIO())

    def test_connect_to_nonexistent_port(self):
        sub = Subscriber()
        with pytest.raises((ConnectionRefusedError, TimeoutError, OSError)):
            sub.connect(port=1, timeout=0.5)

    def test_receive_blocks(self):
        """Subscriber receives blocks from a mock publisher."""
        blocks = [b"\x01\x02\x03\x04", b"\x05\x06\x07\x08", b"\x09\x0A\x0B\x0C"]
        port_holder = []

        pub_thread = threading.Thread(
            target=_mock_publisher, args=(port_holder, 1, blocks)
        )
        pub_thread.start()

        # Wait for publisher to bind
        while not port_holder:
            pass
        port = port_holder[0]

        dest = io.BytesIO()
        sub = Subscriber()
        sub.connect(port, timeout=5.0)
        block_count = sub.receive(dest)
        sub.close()

        pub_thread.join(timeout=5.0)

        assert block_count == 3
        assert dest.getvalue() == b"".join(blocks)

    def test_receive_empty_stream(self):
        """Subscriber handles EOF with zero blocks."""
        port_holder = []

        pub_thread = threading.Thread(
            target=_mock_publisher, args=(port_holder, 1, [])
        )
        pub_thread.start()

        while not port_holder:
            pass
        port = port_holder[0]

        dest = io.BytesIO()
        sub = Subscriber()
        sub.connect(port, timeout=5.0)
        block_count = sub.receive(dest)
        sub.close()

        pub_thread.join(timeout=5.0)

        assert block_count == 0
        assert dest.getvalue() == b""

    def test_variable_block_sizes(self):
        """Subscriber handles blocks of different sizes."""
        blocks = [b"\xFF" * 100, b"\xAA" * 50, b"\x00" * 200]
        port_holder = []

        pub_thread = threading.Thread(
            target=_mock_publisher, args=(port_holder, 1, blocks)
        )
        pub_thread.start()

        while not port_holder:
            pass
        port = port_holder[0]

        dest = io.BytesIO()
        sub = Subscriber()
        sub.connect(port, timeout=5.0)
        block_count = sub.receive(dest)
        sub.close()

        pub_thread.join(timeout=5.0)

        assert block_count == 3
        assert dest.getvalue() == b"".join(blocks)

    def test_close_is_idempotent(self):
        sub = Subscriber()
        sub.close()  # should not raise
        sub.close()  # should not raise
