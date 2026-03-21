"""Entry point for ec-sub: binary stream subscriber.

Connects to an ec-pub publisher via topic discovery and writes
received binary blocks to stdout.

Usage:
    ec-sub --topic demo | ec-beamform --array array.json --stream stream.json | ...
"""

import logging
import sys
import time
import argparse

from common.log import setup_logging
from common.topic import read_topic, is_process_alive
from ec_sub.subscriber import Subscriber

TOOL_NAME = "ec-sub"

logger = logging.getLogger(__name__)

# Retry parameters for topic file discovery
_POLL_INTERVAL = 0.1  # seconds between retries


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Subscribe to binary stream blocks from ec-pub via TCP"
    )
    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="Topic name to subscribe to",
    )
    parser.add_argument(
        "--topic-dir",
        type=str,
        default=None,
        help="Directory for topic files (overrides ECHOCRAFT_TOPIC_DIR and default)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds waiting for publisher (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def _wait_for_topic(
    topic_name: str, timeout: float, topic_dir: str | None = None
) -> int:
    """Wait for topic file to appear and return publisher port.

    Polls for the topic file until it appears or timeout is reached.
    Validates that the publisher process is still alive.

    Args:
        topic_name: Name of the topic to wait for.
        timeout: Maximum seconds to wait.
        topic_dir: Explicit topic directory (from --topic-dir).

    Returns:
        Port number of the publisher.

    Raises:
        TimeoutError: If topic file does not appear within timeout.
        RuntimeError: If publisher process is dead.
    """
    max_attempts = int(timeout / _POLL_INTERVAL)
    for attempt in range(max_attempts):
        try:
            topic_info = read_topic(topic_name, explicit_dir=topic_dir)
            # Verify publisher is alive
            if not is_process_alive(topic_info.pid):
                raise RuntimeError(
                    f"Publisher (PID {topic_info.pid}) is not running. "
                    f"Stale topic file?"
                )
            logger.debug(
                "Found topic '%s': port=%d, pid=%d",
                topic_name,
                topic_info.port,
                topic_info.pid,
            )
            return topic_info.port
        except FileNotFoundError:
            if attempt % 50 == 0 and attempt > 0:
                logger.debug(
                    "Waiting for topic '%s'... (%.1fs elapsed)",
                    topic_name,
                    attempt * _POLL_INTERVAL,
                )
            time.sleep(_POLL_INTERVAL)

    raise TimeoutError(
        f"Topic '{topic_name}' not found after {timeout}s"
    )


def main(argv: list[str] | None = None) -> int:
    """Main entry point for ec-sub.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    args = parse_args(argv)
    setup_logging(args.verbose, tool_name=TOOL_NAME)

    subscriber = Subscriber()

    try:
        # Discover publisher via topic file
        port = _wait_for_topic(args.topic, args.timeout, topic_dir=args.topic_dir)

        # Connect to publisher
        subscriber.connect(port, timeout=args.timeout)

        # Receive blocks and write to stdout
        block_count = subscriber.receive(sys.stdout.buffer)
        logger.info("Received %d blocks from topic '%s'", block_count, args.topic)

        return 0

    except TimeoutError as e:
        logger.error("Timeout: %s", e)
        return 1
    except ConnectionError as e:
        logger.error("Connection error: %s", e)
        return 1
    except RuntimeError as e:
        logger.error("Runtime error: %s", e)
        return 1
    except BrokenPipeError:
        # Downstream closed (normal in pipelines, e.g., head)
        logger.debug("Downstream pipe closed")
        return 0
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return 1
    finally:
        subscriber.close()


if __name__ == "__main__":
    sys.exit(main())
