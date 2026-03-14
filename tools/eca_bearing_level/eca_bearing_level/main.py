"""Entry point for eca-bearing-level: binary to bearing NDJSON converter."""

import argparse
import json
import logging
import sys
import numpy as np
from common.stream import StreamConfig
from common.ndjson import NdjsonWriter
from common.log import setup_logging
from .bearing import BearingLevelAnalyzer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute bearing level by sweeping DAS beamformer across azimuths",
    )
    parser.add_argument("--array", type=str, required=True, help="Path to array.json")
    parser.add_argument("--stream", type=str, required=True, help="Path to stream.json")
    parser.add_argument("--az-start", type=float, default=0.0, help="Start azimuth in degrees (default: 0)")
    parser.add_argument("--az-end", type=float, default=180.0, help="End azimuth in degrees (default: 180)")
    parser.add_argument("--az-step", type=float, default=1.0, help="Azimuth step in degrees (default: 1)")
    parser.add_argument("--steer-el", type=float, default=0.0, help="Steering elevation in degrees (default: 0)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    
    # Load configs
    stream_config = StreamConfig.from_file(args.stream)
    with open(args.array) as f:
        array_config = json.load(f)
    
    sensors = array_config["sensors"]
    n_channels = len(sensors)
    
    # Create analyzer
    analyzer = BearingLevelAnalyzer(
        sensors=sensors,
        stream_config=stream_config,
        az_start=args.az_start,
        az_end=args.az_end,
        az_step=args.az_step,
        steer_el=args.steer_el,
    )
    
    writer = NdjsonWriter(sys.stdout)
    
    block_size = stream_config.block_size
    bytes_per_sample = 4
    block_bytes = n_channels * block_size * bytes_per_sample
    block_count = 0
    
    logger.debug(f"Reading binary blocks: {n_channels} channels, {block_size} samples/block")
    
    while True:
        raw_data = sys.stdin.buffer.read(block_bytes)
        if not raw_data or len(raw_data) < block_bytes:
            break
        
        block = np.frombuffer(raw_data, dtype=np.float32).reshape(n_channels, block_size)
        
        records = analyzer.analyze_block(block, block_index=block_count, rate=stream_config.rate)
        for record in records:
            writer.write(record)
        
        block_count += 1
    
    logger.debug(f"Analyzed {block_count} blocks")


if __name__ == "__main__":
    main()
