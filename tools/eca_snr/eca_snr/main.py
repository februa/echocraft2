"""Entry point for eca-snr: SNR estimation."""

import argparse
import logging
import sys
from common.ndjson import NdjsonReader, NdjsonWriter
from common.log import setup_logging
from .snr import SnrEstimator

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Estimate signal-to-noise ratio from spectrum records",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for eca-snr.
    
    Reads NDJSON records from stdin, collects spectrum and scalar records,
    extracts peak_freq from scalars if available, estimates SNR,
    and writes all records including SNR scalar.
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    # Create NDJSON reader and writer
    reader = NdjsonReader(sys.stdin)
    writer = NdjsonWriter(sys.stdout)
    
    logger.debug("Reading NDJSON records from stdin")
    
    spectrum_records = []
    all_records = []
    peak_freq = None
    
    try:
        for record in reader:
            all_records.append(record)
            
            if record.get("type") == "spectrum":
                spectrum_records.append(record)
            elif record.get("type") == "scalar" and record.get("key") == "peak_freq":
                peak_freq = record.get("value")
    except ValueError as e:
        logger.error(f"Error reading NDJSON: {e}")
        sys.exit(1)
    
    logger.debug(f"Collected {len(spectrum_records)} spectrum records, "
                f"peak_freq={peak_freq}")
    
    # Estimate SNR
    snr_record = SnrEstimator.estimate(spectrum_records, peak_freq)
    logger.debug(f"SNR: {snr_record['value']:.2f} dB")
    
    # Write SNR record first
    writer.write(snr_record)
    
    # Pass through all original records
    for record in all_records:
        writer.write(record)
    
    logger.debug("SNR estimation complete")


if __name__ == "__main__":
    main()
