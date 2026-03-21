"""Entry point for ec-sample: NDJSON to binary PCM converter."""

import argparse
import logging
import sys
from typing import Optional

import numpy as np

from common.log import setup_logging
from common.ndjson import NdjsonReader
from common.record import RecordValidationError, validate_record
from common.scenario import ScenarioConfig, resolve_config_path
from common.stream import StreamConfig
from .sampler import BlockSampler

TOOL_NAME = "ec-sample"

logger = logging.getLogger(__name__)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional list of arguments (for testing). If None, sys.argv[1:] is used.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Convert NDJSON transfer/noise records to binary PCM blocks",
    )
    parser.add_argument(
        "--stream",
        type=str,
        default=None,
        help="Path to stream.json configuration file",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Path to scenario.json (provides default config paths)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        required=True,
        help="Duration of audio to generate in seconds",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for ec-sample.

    Reads NDJSON records from stdin containing transfer functions and noise
    configuration, generates binary PCM float32 blocks, and writes to stdout.

    Args:
        argv: Optional list of arguments (for testing).
    """
    args = parse_args(argv)
    setup_logging(args.verbose, tool_name=TOOL_NAME)

    # Resolve config paths
    scenario = (
        ScenarioConfig.from_file(args.scenario) if args.scenario else None
    )
    stream_path = resolve_config_path(
        explicit=args.stream,
        scenario=scenario,
        field="stream",
        required=True,
        tool_name=TOOL_NAME,
    )

    logger.debug("Loading stream config from %s", stream_path)
    stream_config = StreamConfig.from_file(stream_path)
    logger.debug(
        "Stream config: sample_rate=%d, rate=%d, block_size=%d",
        stream_config.sample_rate, stream_config.rate, stream_config.block_size,
    )

    # Read all NDJSON records from stdin
    logger.debug("Reading NDJSON records from stdin")
    reader = NdjsonReader(sys.stdin)
    transfers = []
    noise_level = None

    for record in reader:
        validate_record(record)
        if record.get("type") == "transfer":
            transfers.append(record)
        elif record.get("type") == "noise":
            noise_level = record.get("level")

    logger.debug(
        "Loaded %d transfer records, noise_level=%s",
        len(transfers), noise_level,
    )

    # Determine number of channels
    if transfers:
        n_channels = max(t["sensor_id"] for t in transfers) + 1
    else:
        n_channels = 1

    logger.debug("Number of channels: %d", n_channels)

    # Compute number of blocks
    n_blocks = int(args.duration * stream_config.rate)
    logger.debug(
        "Generating %d blocks for %s seconds", n_blocks, args.duration,
    )

    # Create sampler and generate blocks
    sampler = BlockSampler(transfers, noise_level, stream_config, n_channels)

    for block_index in range(n_blocks):
        block = sampler.generate_block(block_index)
        # Write in channel-major order
        sys.stdout.buffer.write(block.astype(np.float32).tobytes())

    logger.debug("Block generation complete")


if __name__ == "__main__":
    main()
