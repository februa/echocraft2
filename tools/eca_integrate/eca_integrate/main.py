"""Entry point for eca-integrate: spectrum integration via EMA."""

import argparse
import logging
import sys
from common.ndjson import NdjsonReader, NdjsonWriter
from common.log import setup_logging
from .integrator import EmaIntegrator

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Integrate spectrum records using exponential moving average",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["ema"],
        default="ema",
        help="Integration method (default: ema)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.1,
        help="EMA smoothing factor (default: 0.1)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for eca-integrate.
    
    Reads NDJSON spectrum records from stdin, integrates using EMA,
    and writes integrated records to stdout. Passes through non-spectrum records.
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    logger.debug(f"Initializing integrator: method={args.method}, alpha={args.alpha}")
    integrator = EmaIntegrator(args.alpha)
    
    # Create NDJSON reader and writer
    reader = NdjsonReader(sys.stdin)
    writer = NdjsonWriter(sys.stdout)
    
    logger.debug("Reading NDJSON records from stdin")
    block_count = 0
    
    try:
        for record in reader:
            if record.get("type") == "spectrum":
                # Collect spectrum records for this block
                # Since we get one spectrum record per frequency bin per block,
                # we need to group by blocks. For simplicity, integrate each record
                # individually and output immediately.
                integrated = integrator.integrate([record])
                
                # Write only the updated record (last in the list)
                if integrated:
                    writer.write(integrated[-1])
            else:
                # Pass through non-spectrum records
                writer.write(record)
    except ValueError as e:
        logger.error(f"Error reading NDJSON: {e}")
        sys.exit(1)
    
    logger.debug("Integration complete")


if __name__ == "__main__":
    main()
