import argparse
import os
from pathlib import Path
from importlib.metadata import version

from . import app

DIST_NAME = 'manga-optimiser'

DEFAULT_OUTPUT_PATH = Path('./var/output/')
DEFAULT_FORMATS = ['cbz']
DEFAULT_FLOW_DIRECTION = 'horizontal-rl'
DEFAULT_WORKERS = 4
CORES = os.cpu_count()

WRITING_MODE_ALIASES = {
    'lr': 'horizontal-lr',
    'rl': 'horizontal-rl',
}

# alias don't need to be present, as choices will be matched against after parsing type
WRITING_MODES = ('horizontal-lr', 'horizontal-rl')

try:
    __version__ = version(DIST_NAME)
except:
    __version__ = 'unknown'


def build_parser():
    parser = argparse.ArgumentParser(
        description='Pack and process images from a folder to a CBZ/EPUB file optimized for e-readers like Kobo Clara Color'
    )
    
    parser.add_argument(
        'input_path',
        type=Path,
        help='Path to the image file'
    )

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    parser.add_argument(
        '-r',
        '--recursive',
        type=bool,
        default=False,
        help='Should handle subfolders as individual ebooks'
    )

    parser.add_argument(
        '-o',
        '--output-path',
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help='Where to export the ebook'
    )

    parser.add_argument(
        '-f',
        '--formats',
        choices=app.OUTPUT_FORMATS,
        type=str,
        nargs='+',
        default=DEFAULT_FORMATS,
        help='Output formats'
    )

    parser.add_argument(
        '-d',
        '--flow-direction',
        type=parse_writing_mode,
        default=DEFAULT_FLOW_DIRECTION,
        choices=WRITING_MODES,
        help='Page turning direction (default: horizontal-rl)',
    )

    parser.add_argument(
        '-w',
        '--workers',
        type=int,
        default=DEFAULT_WORKERS,
        choices=range(1,CORES+1),
        help='Number of parallel threads'
    )
    return parser

def parse_writing_mode(value: str) -> str:
    value = value.lower()
    # WRITING_MODE_ALIASES.get(key, fallback)
    # Input "rl" - returns "horizontal-rl"
    # Input "horizontal-lr" - key not found, so returns the fallback "horizontal-lr"
    return WRITING_MODE_ALIASES.get(value, value)


def kindlegen_available() -> bool:
    from shutil import which
    kindlegen = os.getenv('KINDLEGEN')
    if not kindlegen:
        kindlegen = which("kindlegen")  # Searches PATH for the executable
    return kindlegen != None



def has_files(directory: Path) -> bool:
    file_count = sum(
        1 
        for entry in os.scandir(directory)
        if entry.is_file()
    )
    return file_count >= 2

def validate_input_path(input_path: Path) -> int:
    # TODO:
    # if recursive
    # get subdir
    subdirs = [
        path for path in input_path.iterdir()
        if path.is_dir()
    ]
    for dir in subdirs:
        # check if suitable
        return
    return 1


def main() -> int:
    print('Running the application v2')

    parser = build_parser()
    args = parser.parse_args()

    if (
        not args.recursive and has_files(args.input_path) == False
        or args.input_path.is_file()
        ):
        raise ValueError('Input path should be a directory containing images')

    if 'mobi' in args.formats and not kindlegen_available():
        raise RuntimeError(
            "kindlegen is required. Install it and ensure it is on PATH."
        )

    app.main(args.input_path, args.output_path, args.formats, args.flow_direction, args.workers)
    
    return 0
