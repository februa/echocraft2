"""Entry point for ec-source-nb tool."""

import argparse
import sys
from typing import Optional

from common.ndjson import NdjsonWriter
from ec_source_nb.source import NarrowbandSource


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        argv: Optional list of arguments (for testing). If None, sys.argv[1:] is used.
        
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Generate narrowband acoustic sources in NDJSON format"
    )
    parser.add_argument(
        "--freq",
        type=str,
        required=True,
        help="Comma-separated list of frequencies in Hz"
    )
    parser.add_argument(
        "--sl",
        type=str,
        required=True,
        help="Comma-separated list of source levels in dB re 1 μPa"
    )
    parser.add_argument(
        "--az",
        type=str,
        required=True,
        help="Comma-separated list of azimuths in degrees"
    )
    parser.add_argument(
        "--el",
        type=str,
        required=True,
        help="Comma-separated list of elevations in degrees"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for ec-source-nb.
    
    Args:
        argv: Optional list of arguments (for testing).
        
    Returns:
        Exit code (0 on success, 1 on error).
    """
    try:
        args = parse_args(argv)
        
        # Parse comma-separated values
        freqs = [float(x.strip()) for x in args.freq.split(",")]
        sls = [float(x.strip()) for x in args.sl.split(",")]
        azs = [float(x.strip()) for x in args.az.split(",")]
        els = [float(x.strip()) for x in args.el.split(",")]
        
        # Check that all lists have the same length
        if not (len(freqs) == len(sls) == len(azs) == len(els)):
            raise ValueError(
                f"Mismatched argument lengths: "
                f"freq={len(freqs)}, sl={len(sls)}, az={len(azs)}, el={len(els)}"
            )
        
        # Create sources and write to stdout
        writer = NdjsonWriter(sys.stdout)
        
        for freq, sl, az, el in zip(freqs, sls, azs, els):
            source = NarrowbandSource(freq, sl, az, el)
            record = source.to_record()
            writer.write(record.to_dict())
        
        return 0
    
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
