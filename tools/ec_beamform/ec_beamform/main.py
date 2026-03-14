"""Entry point for ec-beamform: binary beamforming processor."""

import argparse
import json
import logging
import sys
import numpy as np
from common.stream import StreamConfig
from common.log import setup_logging
from .beamformer import DelayAndSumBeamformer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Apply delay-and-sum beamforming to binary audio blocks",
    )
    parser.add_argument(
        "--array",
        type=str,
        required=True,
        help="Path to array.json configuration file",
    )
    parser.add_argument(
        "--stream",
        type=str,
        required=True,
        help="Path to stream.json configuration file",
    )
    parser.add_argument(
        "--steer-az",
        type=float,
        default=0.0,
        help="Steering azimuth in degrees (default 0)",
    )
    parser.add_argument(
        "--steer-el",
        type=float,
        default=0.0,
        help="Steering elevation in degrees (default 0)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for ec-beamform.
    
    Reads binary audio blocks from stdin, applies delay-and-sum beamforming
    with specified steering direction, and writes beamformed output to stdout.
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    logger.debug(f"Loading stream config from {args.stream}")
    stream_config = StreamConfig.from_file(args.stream)
    logger.debug(f"Stream config: sample_rate={stream_config.sample_rate}, "
                f"block_size={stream_config.block_size}")
    
    logger.debug(f"Loading array config from {args.array}")
    with open(args.array, 'r') as f:
        array_config = json.load(f)
    sensors = array_config.get("sensors", [])
    logger.debug(f"Loaded {len(sensors)} sensors")
    
    # Create beamformer
    beamformer = DelayAndSumBeamformer(
        sensors,
        stream_config,
        steer_az=args.steer_az,
        steer_el=args.steer_el,
    )
    
    # Determine number of channels from first block
    block_size = stream_config.block_size
    bytes_per_sample = 4  # float32
    
    logger.debug("Reading binary blocks from stdin")
    block_count = 0
    
    while True:
        # Read block data
        raw_data = sys.stdin.buffer.read(len(sensors) * block_size * bytes_per_sample)
        if not raw_data:
            break
        
        # Convert to numpy array and reshape
        block = np.frombuffer(raw_data, dtype=np.float32)
        block = block.reshape(len(sensors), block_size)
        
        # Process block
        output = beamformer.process_block(block)
        
        # Write output
        sys.stdout.buffer.write(output.astype(np.float32).tobytes())
        
        block_count += 1
    
    logger.debug(f"Processed {block_count} blocks")


if __name__ == "__main__":
    main()
