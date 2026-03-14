"""Entry point for ec-propagate tool."""

import argparse
import json
import sys
from typing import Optional

from common.ndjson import NdjsonReader, NdjsonWriter
from ec_propagate.propagate import PlaneWavePropagator


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        argv: Optional list of arguments (for testing). If None, sys.argv[1:] is used.
        
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Apply propagation loss to acoustic sources"
    )
    parser.add_argument(
        "--env",
        type=str,
        required=True,
        help="Path to ocean configuration JSON file"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="plane-wave",
        help="Propagation model name (default: plane-wave)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for ec-propagate.
    
    Reads NDJSON records from stdin, applies propagation loss to source records,
    passes through other records unchanged, and writes to stdout.
    
    Args:
        argv: Optional list of arguments (for testing).
        
    Returns:
        Exit code (0 on success, 1 on error).
    """
    try:
        args = parse_args(argv)
        
        # Load ocean configuration
        with open(args.env, 'r') as f:
            ocean_config = json.load(f)
        
        # Create propagator
        propagator = PlaneWavePropagator(ocean_config, args.model)
        
        # Process records
        reader = NdjsonReader(sys.stdin)
        writer = NdjsonWriter(sys.stdout)
        
        for record in reader:
            processed_record = propagator.propagate(record)
            writer.write(processed_record)
        
        return 0
    
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in ocean config: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
