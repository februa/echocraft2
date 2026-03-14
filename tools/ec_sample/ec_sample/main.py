"""Entry point for ec-sample: NDJSON to binary PCM converter."""

import argparse
import logging
import sys
import numpy as np
from common.ndjson import NdjsonReader
from common.stream import StreamConfig
from common.log import setup_logging
from .sampler import BlockSampler

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Convert NDJSON transfer/noise records to binary PCM blocks",
    )
    parser.add_argument(
        "--stream",
        type=str,
        required=True,
        help="Path to stream.json configuration file",
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
    return parser.parse_args()


def main() -> None:
    """Main entry point for ec-sample.
    
    Reads NDJSON records from stdin containing transfer functions and noise
    configuration, generates binary PCM float32 blocks, and writes to stdout.
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    logger.debug(f"Loading stream config from {args.stream}")
    stream_config = StreamConfig.from_file(args.stream)
    logger.debug(f"Stream config: sample_rate={stream_config.sample_rate}, "
                f"rate={stream_config.rate}, block_size={stream_config.block_size}")
    
    # Read all NDJSON records from stdin
    logger.debug("Reading NDJSON records from stdin")
    reader = NdjsonReader(sys.stdin)
    transfers = []
    noise_level = None
    
    for record in reader:
        if record.get("type") == "transfer":
            transfers.append(record)
        elif record.get("type") == "noise":
            noise_level = record.get("level")
    
    logger.debug(f"Loaded {len(transfers)} transfer records, noise_level={noise_level}")
    
    # Determine number of channels
    if transfers:
        n_channels = max(t["sensor_id"] for t in transfers) + 1
    else:
        n_channels = 1
    
    logger.debug(f"Number of channels: {n_channels}")
    
    # Compute number of blocks
    n_blocks = int(args.duration * stream_config.rate)
    logger.debug(f"Generating {n_blocks} blocks for {args.duration} seconds")
    
    # Create sampler and generate blocks
    sampler = BlockSampler(transfers, noise_level, stream_config, n_channels)
    
    for block_index in range(n_blocks):
        block = sampler.generate_block(block_index)
        # Write in channel-major order
        sys.stdout.buffer.write(block.astype(np.float32).tobytes())
    
    logger.debug("Block generation complete")


if __name__ == "__main__":
    main()
