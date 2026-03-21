"""Integration test: ec-pub/ec-sub with real binary stream data.

Verifies that data published through ec-pub and received via ec-sub
is byte-identical to the original stream.
"""

import io
import struct
import threading

import numpy as np
import pytest

from ec_pub.publisher import Publisher
from ec_sub.subscriber import Subscriber


class TestPubSubIntegration:
    """End-to-end tests simulating real ECHOCRAFT binary streams."""

    def test_multichannel_float32_blocks(self):
        """Simulate a 12-channel, 1024-sample block stream."""
        n_channels = 12
        block_size = 1024
        n_blocks = 10
        n_subscribers = 3

        # Generate realistic float32 audio data
        rng = np.random.default_rng(42)
        all_blocks = []
        for _ in range(n_blocks):
            block = rng.standard_normal((n_channels, block_size)).astype(
                np.float32
            )
            all_blocks.append(block.tobytes())

        source_data = b"".join(all_blocks)
        block_byte_size = n_channels * block_size * 4  # float32 = 4 bytes

        # Setup publisher
        pub = Publisher(n_subscribers=n_subscribers)
        port = pub.bind()

        # Collect results from each subscriber
        results = [io.BytesIO() for _ in range(n_subscribers)]
        errors = []

        def subscriber_fn(index):
            try:
                sub = Subscriber()
                sub.connect(port, timeout=10.0)
                sub.receive(results[index])
                sub.close()
            except Exception as e:
                errors.append((index, e))

        # Start subscribers
        threads = [
            threading.Thread(target=subscriber_fn, args=(i,))
            for i in range(n_subscribers)
        ]
        for t in threads:
            t.start()

        # Publish
        pub.accept_subscribers(timeout=10.0)
        source = io.BytesIO(source_data)
        block_count = pub.publish(source, block_byte_size)
        pub.close()

        # Wait for completion
        for t in threads:
            t.join(timeout=10.0)

        # Verify
        assert not errors, f"Errors: {errors}"
        assert block_count == n_blocks

        for i in range(n_subscribers):
            received = results[i].getvalue()
            assert len(received) == len(source_data), (
                f"Subscriber {i}: expected {len(source_data)} bytes, "
                f"got {len(received)}"
            )
            assert received == source_data, (
                f"Subscriber {i}: data mismatch"
            )

            # Verify numpy can reconstruct the blocks
            arr = np.frombuffer(received, dtype=np.float32)
            arr = arr.reshape(n_blocks, n_channels, block_size)
            expected = np.frombuffer(source_data, dtype=np.float32)
            expected = expected.reshape(n_blocks, n_channels, block_size)
            np.testing.assert_array_equal(arr, expected)

    def test_single_channel_stream(self):
        """Post-beamform scenario: single channel output fan-out."""
        n_channels = 1
        block_size = 512
        n_blocks = 5
        n_subscribers = 2

        rng = np.random.default_rng(123)
        source_data = rng.standard_normal(
            n_blocks * n_channels * block_size
        ).astype(np.float32).tobytes()
        block_byte_size = n_channels * block_size * 4

        pub = Publisher(n_subscribers=n_subscribers)
        port = pub.bind()

        results = [io.BytesIO() for _ in range(n_subscribers)]
        errors = []

        def subscriber_fn(index):
            try:
                sub = Subscriber()
                sub.connect(port, timeout=10.0)
                sub.receive(results[index])
                sub.close()
            except Exception as e:
                errors.append((index, e))

        threads = [
            threading.Thread(target=subscriber_fn, args=(i,))
            for i in range(n_subscribers)
        ]
        for t in threads:
            t.start()

        pub.accept_subscribers(timeout=10.0)
        block_count = pub.publish(io.BytesIO(source_data), block_byte_size)
        pub.close()

        for t in threads:
            t.join(timeout=10.0)

        assert not errors
        assert block_count == n_blocks
        for i in range(n_subscribers):
            assert results[i].getvalue() == source_data
