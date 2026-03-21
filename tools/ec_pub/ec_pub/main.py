"""Entry point for ec-pub: binary stream publisher.

Reads binary blocks from stdin and distributes them to N subscribers
via TCP. Publishes a topic file so that ec-sub can discover the port.

Usage:
    ec-source-nb ... | ec-sample ... \\
      | ec-pub --stream stream.json --array array.json --topic demo --subscribers 3
"""

import json
import logging
import os
import signal
import sys
import argparse

from common.log import setup_logging
from common.stream import StreamConfig
from common.topic import TopicInfo, write_topic, remove_topic
from ec_pub.publisher import Publisher

TOOL_NAME = "ec-pub"

logger = logging.getLogger(__name__)

_BYTES_PER_SAMPLE = 4  # float32


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Publish binary stream blocks to multiple subscribers via TCP"
    )
    parser.add_argument(
        "--stream",
        type=str,
        required=True,
        help="Path to stream.json configuration file",
    )
    parser.add_argument(
        "--array",
        type=str,
        required=True,
        help="Path to array.json configuration file",
    )
    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="Topic name for subscriber discovery",
    )
    parser.add_argument(
        "--subscribers",
        type=int,
        required=True,
        help="Number of subscribers to wait for before publishing",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds waiting for subscribers (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ec-pub.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args(argv)
    setup_logging(args.verbose, tool_name=TOOL_NAME)

    # Load configs
    stream_config = StreamConfig.from_file(args.stream)
    logger.debug(
        "Stream config: sample_rate=%d, block_size=%d",
        stream_config.sample_rate,
        stream_config.block_size,
    )

    with open(args.array, "r") as f:
        array_config = json.load(f)
    sensors = array_config.get("sensors", [])
    n_channels = len(sensors)
    logger.debug("Array config: %d channels", n_channels)

    if n_channels <= 0:
        logger.error("Array must have at least 1 sensor")
        return 1

    block_byte_size = n_channels * stream_config.block_size * _BYTES_PER_SAMPLE
    logger.debug("Block byte size: %d bytes", block_byte_size)

    # Create publisher and bind
    publisher = Publisher(n_subscribers=args.subscribers)
    topic_name = args.topic

    try:
        port = publisher.bind()
        logger.info("Bound to port %d", port)

        # Write topic file for subscriber discovery
        topic_info = TopicInfo(port=port, pid=os.getpid())
        topic_path = write_topic(topic_name, topic_info)
        logger.debug("Topic file written: %s", topic_path)

        # Register cleanup for topic file
        def _cleanup(signum=None, frame=None):
            remove_topic(topic_name)
            publisher.close()
            if signum is not None:
                sys.exit(128 + signum)

        signal.signal(signal.SIGTERM, _cleanup)

        # Wait for subscribers
        logger.info(
            "Waiting for %d subscriber(s) on topic '%s'...",
            args.subscribers,
            topic_name,
        )
        publisher.accept_subscribers(timeout=args.timeout)

        # Publish blocks from stdin
        block_count = publisher.publish(sys.stdin.buffer, block_byte_size)
        logger.info("Published %d blocks", block_count)

        return 0

    except TimeoutError as e:
        logger.error("Timeout: %s", e)
        return 1
    except ConnectionError as e:
        logger.error("Connection error: %s", e)
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return 1
    finally:
        remove_topic(topic_name)
        publisher.close()


if __name__ == "__main__":
    sys.exit(main())
