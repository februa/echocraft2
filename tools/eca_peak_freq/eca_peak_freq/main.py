"""Entry point for eca-peak-freq: peak frequency extraction."""

import argparse
import logging
import sys
from common.ndjson import NdjsonReader, NdjsonWriter
from common.log import setup_logging
from .peak import PeakFrequencyExtractor

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Extract peak frequency from spectrum records",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for eca-peak-freq.
    
    Reads NDJSON records from stdin, collects spectrum records,
    finds peak frequency, writes peak scalar and passes through all records.
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    # Create NDJSON reader and writer
    reader = NdjsonReader(sys.stdin)
    writer = NdjsonWriter(sys.stdout)
    
    logger.debug("Reading NDJSON records from stdin")
    
    spectrum_records = []
    all_records = []
    
    try:
        for record in reader:
            all_records.append(record)
            if record.get("type") == "spectrum":
                spectrum_records.append(record)
    except ValueError as e:
        logger.error(f"Error reading NDJSON: {e}")
        sys.exit(1)
    
    # Find peak frequency
    peak_record = PeakFrequencyExtractor.find_peak(spectrum_records)
    logger.debug(f"Peak frequency: {peak_record['value']} Hz")
    
    # Write peak record first
    writer.write(peak_record)
    
    # Pass through all original records
    for record in all_records:
        writer.write(record)
    
    logger.debug("Peak frequency extraction complete")


if __name__ == "__main__":
    main()
