"""Entry point for ec-array tool."""

import argparse
import json
import sys
from typing import Optional

from common.ndjson import NdjsonReader, NdjsonWriter
from ec_array.array_response import ArrayResponse


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        argv: Optional list of arguments (for testing). If None, sys.argv[1:] is used.
        
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Generate transfer functions for array sensors"
    )
    parser.add_argument(
        "--array",
        type=str,
        required=True,
        help="Path to array configuration JSON file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for ec-array.
    
    Reads NDJSON records from stdin. For each source record, generates
    transfer records for all sensors. Passes through noise records unchanged.
    Writes all records to stdout.
    
    Args:
        argv: Optional list of arguments (for testing).
        
    Returns:
        Exit code (0 on success, 1 on error).
    """
    try:
        args = parse_args(argv)
        
        # Load array configuration
        with open(args.array, 'r') as f:
            array_config = json.load(f)
        
        # Create array response model
        sensors = array_config.get("sensors", [])
        array_response = ArrayResponse(sensors)
        
        # Process records
        reader = NdjsonReader(sys.stdin)
        writer = NdjsonWriter(sys.stdout)
        
        for record in reader:
            record_type = record.get("type")
            
            if record_type == "source":
                # Generate transfer records for this source
                transfers = array_response.compute_transfers(record)
                for transfer in transfers:
                    writer.write(transfer.to_dict())
            elif record_type == "noise":
                # Pass through noise records unchanged
                writer.write(record)
            else:
                # Skip unknown record types
                pass
        
        return 0
    
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in array config: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
