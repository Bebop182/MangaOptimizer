from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.metadata import version
from pathlib import Path
import argparse
import os
import sys

from manga_optimizer.app import main as appmain
from manga_optimizer.model.ebook import Ebook, Page
from manga_optimizer.model.device import Device
from manga_optimizer.constants import DIST_NAME, WRITING_MODES, WRITING_MODE_ALIASES, SUPPORTED_IMAGES, OUTPUT_FORMATS

DEFAULT_OUTPUT_DIR = Path("./var/output/")
DEFAULT_FORMATS = ["cbz"]
DEFAULT_FLOW_DIRECTION = "horizontal-rl"
DEFAULT_IMAGE_WORKERS = 4
DEFAULT_TOME_WORKERS = 2

CORES = os.cpu_count()
__version__ = version(DIST_NAME)


def validate_input_path(input_value: str) -> Path:
    input_path = Path(input_value)
    # input path: exists, is directory, has img content
    if input_path.exists() == False:
        raise argparse.ArgumentTypeError(
            f"input path does not exist: {input_path}")

    if input_path.is_dir() == False:
        raise argparse.ArgumentTypeError(
            f"input path should be a directory of images: {input_path}")

    return input_path


def validate_tome_directory(path: Path) -> Path:
    if path.exists() == False:
        raise argparse.ArgumentTypeError(
            f"input path does not exist: {path}")

    if path.is_dir() == False:
        raise argparse.ArgumentTypeError(
            f"input path should be a directory of images: {path}")

    has_supported_file = any(
        entry.is_file() and entry.suffix.lower() in SUPPORTED_IMAGES
        for entry in path.iterdir()
    )
    if has_supported_file == False:
        raise argparse.ArgumentTypeError(
            "input path doesn't contain supported images")

    return path


def validate_output_dir(output_value: str) -> Path:
    output_path = Path(output_value)
    if output_path.exists() == False:
        raise argparse.ArgumentTypeError("output path does not exist")

    if output_path.is_dir() == False:
        raise argparse.ArgumentTypeError(
            "output path should be a directory")

    if os.access(output_path, os.W_OK) == False:
        raise argparse.ArgumentTypeError(
            f"Write acces required to output path: {output_path}")

    return output_path


def parse_writing_mode(value: str) -> str:
    value = value.lower()
    # WRITING_MODE_ALIASES.get(key, fallback)
    # Input "rl" - returns "horizontal-rl"
    # Input "horizontal-lr" - key not found, so returns the fallback "horizontal-lr"
    return WRITING_MODE_ALIASES.get(value, value)


def get_version() -> str:
    try:
        __version__ = version(DIST_NAME)
    except:
        __version__ = "unknown"
    return __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pack and process images from a folder to a CBZ/EPUB file optimized for e-readers like Kobo Clara Color"
    )

    parser.add_argument(
        "input_path",
        type=validate_input_path,
        help="Path to the image file"
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=validate_output_dir,
        default=DEFAULT_OUTPUT_DIR,
        help="Where to export the ebook"
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}"
    )

    parser.add_argument(
        "--device",
        type=str,
        default="k8",
        help="Target device"
    )

    parser.add_argument(
        "-m",
        "--multi-tome",
        action="store_true",
        help="Should handle subfolders as individual ebooks"
    )

    parser.add_argument(
        "-f",
        "--formats",
        choices=OUTPUT_FORMATS,
        type=str,
        nargs="+",
        default=DEFAULT_FORMATS,
        help="Output formats"
    )

    parser.add_argument(
        "-d",
        "--flow-direction",
        type=parse_writing_mode,
        default=DEFAULT_FLOW_DIRECTION,
        choices=WRITING_MODES,
        help="Page turning direction (default: horizontal-rl)",
    )

    parser.add_argument(
        "-iw",
        "--image-workers",
        type=int,
        default=DEFAULT_IMAGE_WORKERS,
        choices=range(1, CORES+1),
        help="Number of parallel image processing threads"
    )
    parser.add_argument(
        "-tw",
        "--tome-workers",
        type=int,
        default=DEFAULT_TOME_WORKERS,
        choices=range(1, CORES+1),
        help="Number of parallel tome processing threads"
    )
    return parser


def kindlegen_available() -> bool:
    from shutil import which
    kindlegen = os.getenv("KINDLEGEN")
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


def images_from_dir(directory: Path) -> list[Path]:
    image_paths = [
        image_path
        for image_path in directory.iterdir()
        if image_path.is_file() and image_path.suffix.lower() in SUPPORTED_IMAGES
    ]
    return sorted(image_paths, key=lambda path: path.stem.casefold())


def hydrate_tome(title: str, image_paths: list[Path]) -> Ebook:
    cover = Page(
        uri=image_paths[0],
        number=0,
        title="cover"
    )
    pages = [
        Page(
            uri=path,
            title=f"Page {number:03d}",
            number=number
        )
        for number, path in enumerate(image_paths[1:], start=1)
    ]
    book = Ebook(
        title=title,
        cover=cover,
        pages=pages
    )
    return book


def load_device_configs() -> list[Device]:
    # Load device parameter:
    from platformdirs import user_config_dir
    from importlib import resources
    import shutil
    import tomllib

    # user_config_dir provides a platform specific safe dir for config files
    config_dir = Path(user_config_dir(DIST_NAME))
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "devices.toml"

    # if config doesn't exists, copy default over
    if not config_path.exists():
        # pull config
        default_config = resources.files().joinpath("resources", "devices.toml")
        # copy over
        with default_config.open("rb") as source, config_path.open("wb") as destination:
            shutil.copyfileobj(source, destination)

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return {
        short_name: Device.from_config(short_name, values)
        for short_name, values in data["devices"].items()
    }


def discover_tome_directories(root: Path, multi: bool) -> list[Path]:
    if not multi:
        return [validate_tome_directory(root)]

    entries = sorted(
        (
            entry
            for entry in root.iterdir()
            if entry.is_dir()
            and not entry.name.startswith(".")
        ),
        key=lambda path: path.name.casefold(),
    )

    tomes = [
        path
        for path in entries
        if validate_tome_directory(path)
    ]

    if not tomes:
        raise ValueError(
            f"no tome directories containing supported images found in {root}"
        )

    return tomes


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print(f"Running {DIST_NAME} {__version__}...")

    if "mobi" in args.formats and not kindlegen_available():
        raise RuntimeError(
            "kindlegen is required. Please ensure that it is installed and present in PATH."
        )
    # Load device config
    devices = load_device_configs()
    device = devices[args.device]

    tome_paths = discover_tome_directories(args.input_path, args.multi_tome)
    tomes = [
        hydrate_tome(title=tomedir.stem,
                     image_paths=images_from_dir(tomedir))
        for tomedir in tome_paths
    ]

    output_dir = args.output_dir
    formats = args.formats
    image_workers = args.image_workers
    tome_workers = args.tome_workers

    appmain(tomes, device, output_dir,
            formats, image_workers, tome_workers)
