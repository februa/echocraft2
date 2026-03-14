"""Entry point for ecv-spectrum."""

import argparse
import logging
from common.log import setup_logging
from .plotter import SpectrumPlotter

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate spectrum plot from NDJSON")
    parser.add_argument("--input", type=str, required=True, help="Input NDJSON file")
    parser.add_argument("--output", type=str, required=True, help="Output image file (PNG/SVG)")
    parser.add_argument("--scale", type=str, choices=["linear", "log"], default="log", help="Y-axis scale")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    plotter = SpectrumPlotter(scale=args.scale)
    plotter.plot(args.input, args.output)


if __name__ == "__main__":
    main()
