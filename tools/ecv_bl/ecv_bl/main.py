"""Entry point for ecv-bl."""

import argparse
from common.log import setup_logging
from .plotter import BearingLevelPlotter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate bearing level plot from NDJSON")
    parser.add_argument("--input", type=str, required=True, help="Input NDJSON file")
    parser.add_argument("--output", type=str, required=True, help="Output image file")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    plotter = BearingLevelPlotter()
    plotter.plot(args.input, args.output)


if __name__ == "__main__":
    main()
