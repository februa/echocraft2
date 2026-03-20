"""Entry point for ecv-scene: scene overview plotter."""

import argparse
import logging

from common.log import setup_logging
from .plotter import ScenePlotter

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Generate a top-down scene overview plot showing "
        "sensor positions and signal arrival directions",
    )
    parser.add_argument(
        "--array",
        type=str,
        required=True,
        help="Path to array.json configuration file",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to NDJSON file with source/noise records",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output image path (PNG or SVG)",
    )
    parser.add_argument(
        "--heading",
        type=float,
        default=0.0,
        help="Vessel heading in degrees (true north=0, clockwise). "
        "Default 0 means bow points north.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for ecv-scene.

    Reads array.json and source NDJSON, generates a top-down scene
    overview plot showing sensor positions and signal arrival directions.
    """
    args = parse_args()
    setup_logging(args.verbose)

    logger.debug(f"Array config: {args.array}")
    logger.debug(f"Input file: {args.input}")
    logger.debug(f"Output file: {args.output}")

    plotter = ScenePlotter()
    plotter.plot(
        array_path=args.array,
        input_path=args.input,
        output_path=args.output,
        heading_deg=args.heading,
    )


if __name__ == "__main__":
    main()
