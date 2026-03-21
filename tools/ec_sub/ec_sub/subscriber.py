"""Subscriber domain class for binary stream fan-out.

Connects to an ec-pub publisher via TCP and receives binary blocks,
writing them to a destination stream (typically stdout).
"""

import logging
import socket
import struct
from typing import BinaryIO

logger = logging.getLogger(__name__)

# Protocol constants (must match publisher.py)
_HEADER_FORMAT = "!I"  # Network byte order, unsigned 32-bit (block size)
_HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)
_MSG_BLOCK = 1
_MSG_EOF = 0
_MSG_FORMAT = "!B"  # Message type: 1 byte
_MSG_SIZE = struct.calcsize(_MSG_FORMAT)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes from socket.

    Args:
        sock: Connected socket.
        n: Number of bytes to receive.

    Returns:
        Exactly n bytes.

    Raises:
        ConnectionError: If connection is closed before n bytes received.
    """
    chunks = []
    received = 0
    while received < n:
        chunk = sock.recv(n - received)
        if not chunk:
            raise ConnectionError(
                f"Connection closed after {received}/{n} bytes"
            )
        chunks.append(chunk)
        received += len(chunk)
    return b"".join(chunks)


class Subscriber:
    """Receives binary blocks from an ec-pub publisher via TCP.

    Connects to a publisher, receives framed binary blocks, and
    writes them to a destination stream.

    The wire protocol per block is:
        [1 byte msg_type] [4 bytes block_byte_size] [block_byte_size bytes payload]

    EOF is signaled by:
        [1 byte msg_type=0]
    """

    def __init__(self, host: str = "127.0.0.1") -> None:
        """Initialize the subscriber.

        Args:
            host: Host address to connect to.
        """
        self._host = host
        self._sock: socket.socket | None = None

    def connect(self, port: int, timeout: float = 30.0) -> None:
        """Connect to the publisher.

        Args:
            port: TCP port where the publisher is listening.
            timeout: Connection timeout in seconds.

        Raises:
            ConnectionRefusedError: If publisher is not listening.
            TimeoutError: If connection times out.
        """
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        try:
            self._sock.connect((self._host, port))
        except socket.timeout:
            self._sock.close()
            self._sock = None
            raise TimeoutError(
                f"Timed out connecting to {self._host}:{port}"
            )
        # Disable timeout for data transfer (blocking reads)
        self._sock.settimeout(None)
        logger.debug("Connected to publisher at %s:%d", self._host, port)

    def receive(self, dest: BinaryIO) -> int:
        """Receive blocks from publisher and write to destination.

        Reads framed blocks from the TCP connection and writes raw
        block data (without framing) to dest. Continues until the
        publisher sends an EOF signal.

        Args:
            dest: Binary stream to write received blocks to.

        Returns:
            Number of blocks received.

        Raises:
            RuntimeError: If not connected.
            ConnectionError: If connection is broken.
        """
        if self._sock is None:
            raise RuntimeError("Not connected. Call connect() first.")

        block_count = 0

        while True:
            # Read message type
            msg_type_bytes = _recv_exact(self._sock, _MSG_SIZE)
            msg_type = struct.unpack(_MSG_FORMAT, msg_type_bytes)[0]

            if msg_type == _MSG_EOF:
                logger.debug("Received EOF from publisher")
                break

            if msg_type != _MSG_BLOCK:
                raise ConnectionError(
                    f"Unknown message type: {msg_type}"
                )

            # Read block size header
            size_bytes = _recv_exact(self._sock, _HEADER_SIZE)
            block_byte_size = struct.unpack(_HEADER_FORMAT, size_bytes)[0]

            # Read block payload
            block_data = _recv_exact(self._sock, block_byte_size)

            # Write to destination
            dest.write(block_data)
            dest.flush()

            block_count += 1
            if block_count % 100 == 0:
                logger.debug("Received %d blocks", block_count)

        logger.info("Received %d blocks", block_count)
        return block_count

    def close(self) -> None:
        """Close the TCP connection."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            logger.debug("Subscriber closed")
