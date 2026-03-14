"""Entry point for ec-noise tool."""

import argparse
import sys
from typing import Optional

from common.ndjson import NdjsonReader, NdjsonWriter
from ec_noise.noise import NoiseField


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        argv: Optional list of arguments (for testing). If None, sys.argv[1:] is used.
        
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Add ambient noise record to NDJSON stream"
    )
    parser.add_argument(
        "--nl",
        type=float,
        required=True,
        help="Noise level in dB re 1 μPa"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for ec-noise.
    
    Reads NDJSON records from stdin, passes them through to stdout,
    then appends a noise record at the end.
    
    Args:
        argv: Optional list of arguments (for testing).
        
    Returns:
        Exit code (0 on success, 1 on error).
    """
    try:
        args = parse_args(argv)
        
        # Validate noise level
        noise_field = NoiseField(args.nl)
        
        # Read all records from stdin and write to stdout
        reader = NdjsonReader(sys.stdin)
        writer = NdjsonWriter(sys.stdout)
        
        for record in reader:
            writer.write(record)
        
        # Append noise record at the end
        noise_record = noise_field.to_record()
        writer.write(noise_record.to_dict())
        
        return 0
    
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
