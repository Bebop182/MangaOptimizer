import argparse
from pathlib import Path
from . import app

WRITING_MODE_ALIASES = {
    "lr": "horizontal-lr",
    "rl": "horizontal-rl",
}

# alias don't need to be present, as choices will be matched against after parsing type
WRITING_MODES = ("horizontal-lr", "horizontal-rl")

def parse_writing_mode(value: str) -> str:
    value = value.lower()
    # WRITING_MODE_ALIASES.get(key, fallback)
    # Input "rl" - returns "horizontal-rl"
    # Input "horizontal-lr" - key not found, so returns the fallback "horizontal-lr"
    return WRITING_MODE_ALIASES.get(value, value)

def main() -> int:
    print("Running the application")

    parser = argparse.ArgumentParser(
        description="Pack and process images from a folder to a CBZ/EPUB file optimized for e-readers like Kobo Clara Color"
    )
    
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to the image file"
    )

    parser.add_argument(
        "-o",
        "--output-path",
        type=Path,
        default="./output/",
        help="Where to export the CBZ"
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=OUTPUT_FORMATS,
        type=str,
        nargs='+',
        help='Output format'
    )

    parser.add_argument(
        "-d",
        "--flow-direction",
        type=parse_writing_mode,
        choices=WRITING_MODES,
        default="horizontal-rl",
        help="Page turning direction (default: horizontal-rl)",
    )

    parser.add_argument(
        "-w",
        "--worker",
        type=int,
        choices=range(1,CORES+1),
        default=4,
        help='Number of parallel threads'
    )

    args = parser.parse_args()

    manga_optimizer.main(args.input_path, args.output_path, args.formats, args.flow_direction, args.worker_count)
    
    return 0
