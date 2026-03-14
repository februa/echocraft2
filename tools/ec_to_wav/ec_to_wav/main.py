"""Entry point for ec-to-wav: binary to WAV file converter."""

import argparse
import logging
import sys
import numpy as np
from common.stream import StreamConfig
from common.log import setup_logging
from .writer import WavWriter

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Convert binary audio blocks to WAV file",
    )
    parser.add_argument(
        "--stream",
        type=str,
        required=True,
        help="Path to stream.json configuration file",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to output WAV file",
    )
    parser.add_argument(
        "--channels",
        type=int,
        required=True,
        help="Number of audio channels",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for ec-to-wav.
    
    Reads binary audio blocks from stdin and writes to WAV file.
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    logger.debug(f"Loading stream config from {args.stream}")
    stream_config = StreamConfig.from_file(args.stream)
    logger.debug(f"Stream config: sample_rate={stream_config.sample_rate}, "
                f"block_size={stream_config.block_size}")
    
    logger.debug(f"Creating WAV writer: output={args.output}, "
                f"channels={args.channels}")
    writer = WavWriter(args.output, stream_config, args.channels)
    
    block_size = stream_config.block_size
    bytes_per_sample = 4  # float32
    block_count = 0
    
    logger.debug("Reading binary blocks from stdin")
    
    try:
        while True:
            # Read block data
            raw_data = sys.stdin.buffer.read(
                args.channels * block_size * bytes_per_sample
            )
            if not raw_data:
                break
            
            # Convert to numpy array and reshape
            block = np.frombuffer(raw_data, dtype=np.float32)
            block = block.reshape(args.channels, block_size)
            
            # Write to WAV
            writer.write_block(block)
            block_count += 1
    finally:
        writer.close()
    
    logger.debug(f"Wrote {block_count} blocks to {args.output}")


if __name__ == "__main__":
    main()
