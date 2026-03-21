"""Publisher domain class for binary stream fan-out.

Reads binary blocks from a source and distributes copies to all
connected subscribers via TCP sockets. Each subscriber receives
an independent copy of every block.
"""

import logging
import socket
import struct
import threading
from typing import BinaryIO

logger = logging.getLogger(__name__)

# Protocol constants
_HEADER_FORMAT = "!I"  # Network byte order, unsigned 32-bit (block size)
_HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)
_MSG_BLOCK = 1
_MSG_EOF = 0
_MSG_FORMAT = "!B"  # Message type: 1 byte
_MSG_SIZE = struct.calcsize(_MSG_FORMAT)


def _send_all(sock: socket.socket, data: bytes) -> None:
    """Send all bytes through socket, handling partial sends.

    Args:
        sock: Connected socket.
        data: Bytes to send.

    Raises:
        ConnectionError: If connection is broken during send.
    """
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise ConnectionError("Connection broken during send")
        total_sent += sent


class Publisher:
    """Distributes binary blocks to multiple TCP subscribers.

    The publisher binds to a local TCP port, waits for the expected
    number of subscribers to connect, then reads blocks from a binary
    source and sends each block to every subscriber.

    The wire protocol per block is:
        [1 byte msg_type] [4 bytes block_byte_size] [block_byte_size bytes payload]

    EOF is signaled by:
        [1 byte msg_type=0]

    Attributes:
        port: The TCP port the publisher is listening on.
    """

    def __init__(self, n_subscribers: int, host: str = "127.0.0.1") -> None:
        """Initialize the publisher.

        Args:
            n_subscribers: Number of subscribers to wait for before
                starting block distribution.
            host: Host address to bind to.

        Raises:
            ValueError: If n_subscribers < 1.
        """
        if n_subscribers < 1:
            raise ValueError(
                f"n_subscribers must be >= 1, got {n_subscribers}"
            )
        self._n_subscribers = n_subscribers
        self._host = host
        self._server_sock: socket.socket | None = None
        self._subscribers: list[socket.socket] = []

    @property
    def port(self) -> int:
        """Return the bound port number.

        Raises:
            RuntimeError: If server socket is not yet bound.
        """
        if self._server_sock is None:
            raise RuntimeError("Server socket not bound yet")
        addr = self._server_sock.getsockname()
        return addr[1]

    def bind(self) -> int:
        """Bind to an available port and start listening.

        Returns:
            The port number bound to.
        """
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )
        self._server_sock.bind((self._host, 0))  # OS assigns port
        self._server_sock.listen(self._n_subscribers)
        logger.debug(
            "Listening on %s:%d for %d subscriber(s)",
            self._host,
            self.port,
            self._n_subscribers,
        )
        return self.port

    def accept_subscribers(self, timeout: float = 30.0) -> None:
        """Wait for all expected subscribers to connect.

        Args:
            timeout: Maximum seconds to wait for each subscriber.

        Raises:
            TimeoutError: If not all subscribers connect within timeout.
            RuntimeError: If server socket is not bound.
        """
        if self._server_sock is None:
            raise RuntimeError("Must call bind() before accept_subscribers()")

        self._server_sock.settimeout(timeout)
        for i in range(self._n_subscribers):
            try:
                conn, addr = self._server_sock.accept()
                self._subscribers.append(conn)
                logger.debug(
                    "Subscriber %d/%d connected from %s:%d",
                    i + 1,
                    self._n_subscribers,
                    addr[0],
                    addr[1],
                )
            except socket.timeout:
                raise TimeoutError(
                    f"Timed out waiting for subscriber {i + 1}/"
                    f"{self._n_subscribers} (timeout={timeout}s)"
                )
        logger.info("All %d subscriber(s) connected", self._n_subscribers)

    def publish(self, source: BinaryIO, block_byte_size: int) -> int:
        """Read blocks from source and distribute to all subscribers.

        Reads exactly block_byte_size bytes per block from source.
        Each block is sent to every connected subscriber. When source
        is exhausted, sends EOF signal to all subscribers.

        Args:
            source: Binary stream to read blocks from.
            block_byte_size: Size of each block in bytes.

        Returns:
            Number of blocks published.

        Raises:
            ValueError: If block_byte_size <= 0.
            ConnectionError: If a subscriber disconnects during publish.
        """
        if block_byte_size <= 0:
            raise ValueError(
                f"block_byte_size must be positive, got {block_byte_size}"
            )

        block_count = 0
        header_prefix = struct.pack(_MSG_FORMAT, _MSG_BLOCK)
        size_header = struct.pack(_HEADER_FORMAT, block_byte_size)

        while True:
            block = source.read(block_byte_size)
            if not block:
                break
            if len(block) < block_byte_size:
                logger.warning(
                    "Incomplete block: got %d bytes, expected %d (discarded)",
                    len(block),
                    block_byte_size,
                )
                break

            # Send to each subscriber: [msg_type][size][payload]
            frame = header_prefix + size_header + block
            failed = []
            for i, sock in enumerate(self._subscribers):
                try:
                    _send_all(sock, frame)
                except (ConnectionError, OSError) as e:
                    logger.error("Subscriber %d send failed: %s", i, e)
                    failed.append(i)

            if failed:
                raise ConnectionError(
                    f"Subscriber(s) {failed} disconnected during publish"
                )

            block_count += 1
            if block_count % 100 == 0:
                logger.debug("Published %d blocks", block_count)

        # Send EOF to all subscribers
        eof_msg = struct.pack(_MSG_FORMAT, _MSG_EOF)
        for i, sock in enumerate(self._subscribers):
            try:
                _send_all(sock, eof_msg)
            except (ConnectionError, OSError) as e:
                logger.warning("Failed to send EOF to subscriber %d: %s", i, e)

        logger.info("Published %d blocks to %d subscriber(s)",
                     block_count, len(self._subscribers))
        return block_count

    def close(self) -> None:
        """Close all subscriber connections and the server socket."""
        for sock in self._subscribers:
            try:
                sock.close()
            except OSError:
                pass
        self._subscribers.clear()

        if self._server_sock is not None:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None
        logger.debug("Publisher closed")
