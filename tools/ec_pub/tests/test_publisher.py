"""Tests for ec-pub publisher and ec-sub subscriber integration."""

import io
import socket
import struct
import threading
import time

import pytest

from ec_pub.publisher import Publisher, _MSG_BLOCK, _MSG_EOF, _MSG_FORMAT, _HEADER_FORMAT


class TestPublisher:
    """Unit tests for Publisher domain class."""

    def test_invalid_subscriber_count(self):
        with pytest.raises(ValueError, match="n_subscribers must be >= 1"):
            Publisher(n_subscribers=0)

    def test_bind_assigns_port(self):
        pub = Publisher(n_subscribers=1)
        try:
            port = pub.bind()
            assert port > 0
            assert pub.port == port
        finally:
            pub.close()

    def test_port_before_bind_raises(self):
        pub = Publisher(n_subscribers=1)
        with pytest.raises(RuntimeError, match="not bound"):
            _ = pub.port

    def test_accept_before_bind_raises(self):
        pub = Publisher(n_subscribers=1)
        with pytest.raises(RuntimeError, match="Must call bind"):
            pub.accept_subscribers()

    def test_publish_invalid_block_size(self):
        pub = Publisher(n_subscribers=1)
        pub.bind()
        pub._subscribers = [socket.socket()]  # dummy
        with pytest.raises(ValueError, match="block_byte_size must be positive"):
            pub.publish(io.BytesIO(b""), 0)
        pub.close()

    def test_single_subscriber_receives_blocks(self):
        """End-to-end: publisher sends blocks, subscriber receives them."""
        block_size = 16  # 4 float32 samples
        n_blocks = 5
        # Generate test data: n_blocks blocks of block_size bytes each
        test_data = bytes(range(256))[:block_size] * n_blocks
        source = io.BytesIO(test_data)

        pub = Publisher(n_subscribers=1)
        port = pub.bind()

        received_data = bytearray()
        errors = []

        def subscriber_thread():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("127.0.0.1", port))
                while True:
                    # Read message type
                    msg_type_raw = sock.recv(1)
                    if not msg_type_raw:
                        break
                    msg_type = struct.unpack(_MSG_FORMAT, msg_type_raw)[0]
                    if msg_type == _MSG_EOF:
                        break
                    if msg_type == _MSG_BLOCK:
                        size_raw = b""
                        while len(size_raw) < 4:
                            size_raw += sock.recv(4 - len(size_raw))
                        size = struct.unpack(_HEADER_FORMAT, size_raw)[0]
                        payload = b""
                        while len(payload) < size:
                            payload += sock.recv(size - len(payload))
                        received_data.extend(payload)
                sock.close()
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=subscriber_thread)
        t.start()

        pub.accept_subscribers(timeout=5.0)
        block_count = pub.publish(source, block_size)
        pub.close()

        t.join(timeout=5.0)

        assert not errors, f"Subscriber errors: {errors}"
        assert block_count == n_blocks
        assert bytes(received_data) == test_data

    def test_multiple_subscribers(self):
        """Multiple subscribers each receive a full copy of all blocks."""
        block_size = 8
        n_blocks = 3
        n_subs = 3
        test_data = b"\xAA" * block_size * n_blocks
        source = io.BytesIO(test_data)

        pub = Publisher(n_subscribers=n_subs)
        port = pub.bind()

        results = [bytearray() for _ in range(n_subs)]
        errors = []

        def subscriber_thread(index):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("127.0.0.1", port))
                while True:
                    msg_type_raw = sock.recv(1)
                    if not msg_type_raw:
                        break
                    msg_type = struct.unpack(_MSG_FORMAT, msg_type_raw)[0]
                    if msg_type == _MSG_EOF:
                        break
                    if msg_type == _MSG_BLOCK:
                        size_raw = b""
                        while len(size_raw) < 4:
                            size_raw += sock.recv(4 - len(size_raw))
                        size = struct.unpack(_HEADER_FORMAT, size_raw)[0]
                        payload = b""
                        while len(payload) < size:
                            payload += sock.recv(size - len(payload))
                        results[index].extend(payload)
                sock.close()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=subscriber_thread, args=(i,))
            for i in range(n_subs)
        ]
        for t in threads:
            t.start()

        pub.accept_subscribers(timeout=5.0)
        block_count = pub.publish(source, block_size)
        pub.close()

        for t in threads:
            t.join(timeout=5.0)

        assert not errors, f"Subscriber errors: {errors}"
        assert block_count == n_blocks
        for i in range(n_subs):
            assert bytes(results[i]) == test_data, (
                f"Subscriber {i} data mismatch"
            )

    def test_timeout_waiting_for_subscribers(self):
        """Publisher times out if not enough subscribers connect."""
        pub = Publisher(n_subscribers=2)
        pub.bind()

        # Connect only 1 subscriber
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", pub.port))

        with pytest.raises(TimeoutError):
            pub.accept_subscribers(timeout=0.5)

        sock.close()
        pub.close()

    def test_empty_source(self):
        """Publishing from empty source sends 0 blocks + EOF."""
        pub = Publisher(n_subscribers=1)
        port = pub.bind()

        received_eof = [False]
        errors = []

        def subscriber_thread():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("127.0.0.1", port))
                msg_type_raw = sock.recv(1)
                msg_type = struct.unpack(_MSG_FORMAT, msg_type_raw)[0]
                if msg_type == _MSG_EOF:
                    received_eof[0] = True
                sock.close()
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=subscriber_thread)
        t.start()

        pub.accept_subscribers(timeout=5.0)
        block_count = pub.publish(io.BytesIO(b""), 16)
        pub.close()

        t.join(timeout=5.0)

        assert not errors
        assert block_count == 0
        assert received_eof[0]
