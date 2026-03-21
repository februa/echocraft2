"""Entry point for eca-spectrum: binary to spectrum NDJSON converter."""

import argparse
import logging
import sys
import numpy as np
from common.stream import StreamConfig
from common.ndjson import NdjsonWriter
from common.log import setup_logging
from .spectrum import SpectrumAnalyzer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Convert binary audio blocks to spectrum NDJSON records",
    )
    parser.add_argument(
        "--stream",
        type=str,
        required=True,
        help="Path to stream.json configuration file",
    )
    parser.add_argument(
        "--window",
        type=str,
        default="hanning",
        choices=["rectangular", "hanning", "hamming", "blackman"],
        help="Window function for FFT (default: hanning)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for eca-spectrum.
    
    Reads binary audio blocks from stdin, analyzes each for spectrum,
    and writes spectrum records to stdout as NDJSON.
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    logger.debug(f"Loading stream config from {args.stream}")
    stream_config = StreamConfig.from_file(args.stream)
    logger.debug(f"Stream config: sample_rate={stream_config.sample_rate}, "
                f"block_size={stream_config.block_size}")
    
    # Create analyzer
    analyzer = SpectrumAnalyzer(stream_config, window=args.window)
    
    # Create NDJSON writer
    writer = NdjsonWriter(sys.stdout)
    
    block_size = stream_config.block_size
    bytes_per_sample = 4  # float32
    block_count = 0
    
    logger.debug("Reading binary blocks from stdin")
    
    while True:
        # Read one channel block (single beam output from beamformer)
        raw_data = sys.stdin.buffer.read(block_size * bytes_per_sample)
        if not raw_data:
            break
        
        # Convert to numpy array and reshape to (1, block_size)
        block = np.frombuffer(raw_data, dtype=np.float32)
        block = block.reshape(1, block_size)
        
        # Analyze
        records = analyzer.analyze_block(
            block, block_index=block_count, rate=stream_config.rate
        )
        
        # Write spectrum records
        for record in records:
            writer.write(record)
        
        block_count += 1
    
    logger.debug(f"Analyzed {block_count} blocks")


if __name__ == "__main__":
    main()
