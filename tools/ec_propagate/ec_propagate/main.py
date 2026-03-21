"""Entry point for ec-propagate tool."""

import argparse
import json
import logging
import sys
from typing import Optional

from common.log import setup_logging
from common.ndjson import NdjsonReader, NdjsonWriter
from common.record import RecordValidationError, validate_record
from common.scenario import ScenarioConfig, resolve_config_path
from ec_propagate.propagate import PlaneWavePropagator

TOOL_NAME = "ec-propagate"

logger = logging.getLogger(__name__)


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
        default=None,
        help="Path to ocean configuration JSON file"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Path to scenario.json (provides default config paths)"
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
        setup_logging(verbose=args.verbose, tool_name=TOOL_NAME)

        # Resolve config paths
        scenario = (
            ScenarioConfig.from_file(args.scenario) if args.scenario else None
        )
        ocean_path = resolve_config_path(
            explicit=args.env,
            scenario=scenario,
            field="ocean",
            required=True,
            tool_name=TOOL_NAME,
        )

        # Load ocean configuration
        with open(ocean_path, "r") as f:
            ocean_config = json.load(f)

        # Create propagator
        propagator = PlaneWavePropagator(ocean_config, args.model)

        # Process records
        reader = NdjsonReader(sys.stdin)
        writer = NdjsonWriter(sys.stdout)

        for record in reader:
            validate_record(record)
            processed_record = propagator.propagate(record)
            writer.write(processed_record)

        return 0

    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 1
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in ocean config: %s", e)
        return 1
    except RecordValidationError as e:
        logger.error("Invalid record: %s", e)
        return 1
    except ValueError as e:
        logger.error("%s", e)
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
