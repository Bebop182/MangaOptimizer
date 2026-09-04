import argparse
import os
from pathlib import Path
from . import app

DEFAULT_OUTPUT_PATH = './var/output/'
CORES = os.cpu_count()

WRITING_MODE_ALIASES = {
    'lr': 'horizontal-lr',
    'rl': 'horizontal-rl',
}

# alias don't need to be present, as choices will be matched against after parsing type
WRITING_MODES = ('horizontal-lr', 'horizontal-rl')

def parse_writing_mode(value: str) -> str:
    value = value.lower()
    # WRITING_MODE_ALIASES.get(key, fallback)
    # Input "rl" - returns "horizontal-rl"
    # Input "horizontal-lr" - key not found, so returns the fallback "horizontal-lr"
    return WRITING_MODE_ALIASES.get(value, value)

def main() -> int:
    print('Running the application')

    parser = argparse.ArgumentParser(
        description='Pack and process images from a folder to a CBZ/EPUB file optimized for e-readers like Kobo Clara Color'
    )
    
    parser.add_argument(
        'input_path',
        type=Path,
        help='Path to the image file'
    )

    parser.add_argument(
        '-o',
        '--output-path',
        type=Path,
        default=Path(DEFAULT_OUTPUT_PATH),
        help='Where to export the ebook'
    )

    parser.add_argument(
        '-f',
        '--formats',
        choices=app.OUTPUT_FORMATS,
        type=str,
        nargs='+',
        default=['cbz'],
        help='Output formats'
    )

    parser.add_argument(
        '-d',
        '--flow-direction',
        type=parse_writing_mode,
        default='horizontal-rl',
        choices=WRITING_MODES,
        
        help='Page turning direction (default: horizontal-rl)',
    )

    parser.add_argument(
        '-w',
        '--workers',
        type=int,
        default=4,
        choices=range(1,CORES+1),
        help='Number of parallel threads'
    )

    args = parser.parse_args()

    app.main(args.input_path, args.output_path, args.formats, args.flow_direction, args.workers)
    
    return 0
