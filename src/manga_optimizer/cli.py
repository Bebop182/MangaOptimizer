from importlib.metadata import version
from pathlib import Path
import argparse
import os
import sys

from manga_optimizer import app
from manga_optimizer.constants import DIST_NAME, WRITING_MODES, WRITING_MODE_ALIASES

DEFAULT_OUTPUT_PATH = Path('./var/output/')
DEFAULT_FORMATS = ['cbz']
DEFAULT_FLOW_DIRECTION = 'horizontal-rl'
DEFAULT_WORKERS = 4
CORES = os.cpu_count()
__version__ = version(DIST_NAME)


def validate_input_path(input_value: str) -> Path:
    input_path = Path(input_value)
    # input path: exists, is directory, has img content
    if input_path.exists() == False:
        raise argparse.ArgumentTypeError(
            f'input path does not exist: {input_path}')

    if input_path.is_dir() == False:
        raise argparse.ArgumentTypeError(
            f'input path should be a directory of images: {input_path}')

    has_supported_file = any(
        entry.is_file() and entry.suffix.lower() in app.SUPPORTED_IMAGES
        for entry in input_path.iterdir()
    )
    if has_supported_file == False:
        raise argparse.ArgumentTypeError(
            "input path doesn't contain supported images")

    return input_path


def validate_output_path(output_value: str) -> Path:
    output_path = Path(output_value)
    # output path: exists, is writable
    if output_path.exists() == False:
        raise argparse.ArgumentTypeError('output path does not exist')

    if output_path.is_dir() == False:
        raise argparse.ArgumentTypeError(
            'output path should be a directory')

    if os.access(output_path, os.W_OK) == False:
        raise argparse.ArgumentTypeError(
            f'Write acces required to output path: {output_path}')

    return output_path


def parse_writing_mode(value: str) -> str:
    value = value.lower()
    # WRITING_MODE_ALIASES.get(key, fallback)
    # Input "rl" - returns "horizontal-rl"
    # Input "horizontal-lr" - key not found, so returns the fallback "horizontal-lr"
    return WRITING_MODE_ALIASES.get(value, value)


def get_version():
    try:
        __version__ = version(DIST_NAME)
    except:
        __version__ = 'unknown'
    return __version__


def build_parser():
    parser = argparse.ArgumentParser(
        description='Pack and process images from a folder to a CBZ/EPUB file optimized for e-readers like Kobo Clara Color'
    )

    parser.add_argument(
        'input_path',
        type=validate_input_path,
        help='Path to the image file'
    )

    parser.add_argument(
        '-o',
        '--output-path',
        type=validate_output_path,
        default=DEFAULT_OUTPUT_PATH,
        help='Where to export the ebook'
    )

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f"%(prog)s {get_version()}"
    )

    # parser.add_argument(
    #     '-r',
    #     '--recursive',
    #     type=bool,
    #     default=False,
    #     help='Should handle subfolders as individual ebooks'
    # )

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
        choices=range(1, CORES+1),
        help='Number of parallel threads'
    )
    return parser


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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print(f"Running {DIST_NAME} {__version__}...")

    # formats: kindlegen available for mobi
    if 'mobi' in args.formats and not kindlegen_available():
        raise RuntimeError(
            "kindlegen is required. Install it and ensure it is on PATH."
        )

    app.main(args.input_path, args.output_path,
             args.formats, args.flow_direction, args.workers)
