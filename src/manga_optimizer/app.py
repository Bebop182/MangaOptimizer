from concurrent.futures import ThreadPoolExecutor, as_completed
from zipfile import ZIP_DEFLATED, ZipFile
from tempfile import TemporaryDirectory
from collections.abc import Callable
from pathlib import Path
from shutil import move
import argparse

from .export.epub import EpubExporter
from .export.mobi import MobiExporter
from .export.cbz import CBZExporter
from .model.ebook import Ebook, Page
from .model.device import Device
from .constants import SUPPORTED_IMAGES

from PIL import Image
import numpy as np

# Todo:
# Better cropping, removing page number
# Anti-rainbow effect for colored eink using fourier transforms
# improve test coverage
# implement progress logging


def simple_crop(
    image: Image.Image,
    threshold: int = 30,
    padding: int = 8,
) -> Image.Image:
    '''
    Crop a Pillow image to its non-background content.

    Works with black-on-white and white-on-black scans.
    '''
    pixels = np.asarray(image)

    height, width = pixels.shape
    corner_size = max(1, min(height, width) // 25)

    corners = np.concatenate([
        pixels[:corner_size, :corner_size].ravel(),
        pixels[:corner_size, -corner_size:].ravel(),
        pixels[-corner_size:, :corner_size].ravel(),
        pixels[-corner_size:, -corner_size:].ravel(),
    ])

    background = np.median(corners)

    # Pixels sufficiently different from the background are content.
    content = np.abs(pixels.astype(np.int16) - background) > threshold

    ys, xs = np.where(content)

    if len(xs) == 0:
        raise ValueError('No content detected')

    left = max(0, int(xs.min()) - padding)
    top = max(0, int(ys.min()) - padding)
    right = min(width, int(xs.max()) + padding + 1)
    bottom = min(height, int(ys.max()) + padding + 1)

    return image.crop((left, top, right, bottom))


def smart_resize(
    image: Image.Image,
    target_size: tuple[int, int],
    max_deform: int = 10
) -> Image.Image:

    target_width, target_height = target_size
    display_ratio = target_width / target_height
    image_ratio = image.width / image.height
    tolerance = max_deform / 100

    width = target_width
    height = target_height
    if image_ratio > display_ratio:
        # L'image est relativement plus large.
        # On conserve la largeur et on modifie la hauteur.
        # width = pil_image.width
        reduction_factor = image.width / target_width

        required_factor = image_ratio / display_ratio
        applied_factor = min(required_factor, 1.0 + tolerance)

        height = round(image.height * applied_factor / reduction_factor)
        height = min(target_height, height)

    else:
        # L'image est relativement plus haute.
        # On conserve la hauteur et on modifie la largeur.
        reduction_factor = image.height / target_height

        required_factor = display_ratio / image_ratio
        applied_factor = min(required_factor, 1.0 + tolerance)

        width = round(image.width * applied_factor / reduction_factor)
        width = min(target_width, width)

    return image.resize((width, height), resample=Image.Resampling.LANCZOS)


def stretch_contrast(image):
    pixels = np.asarray(image, dtype=np.uint8)

    minimum = int(pixels.min())
    maximum = int(pixels.max())

    if minimum == maximum:
        stretched = np.zeros_like(pixels)
    else:
        stretched = ((pixels.astype(np.float32) - minimum) * 255 /
                     (maximum - minimum)).clip(0, 255).astype(np.uint8)

    return Image.fromarray(stretched, mode='L')


def has_content(image, threshold=12, min_fraction=0.001) -> bool:
    image = image.convert('L')
    image.thumbnail((512, 512))

    pixels = np.asarray(image, dtype=np.int16)

    h, w = pixels.shape
    n = max(1, min(h, w) // 20)

    # Estimate background from the four corners
    corners = np.concatenate([
        pixels[:n, :n].ravel(),
        pixels[:n, -n:].ravel(),
        pixels[-n:, :n].ravel(),
        pixels[-n:, -n:].ravel(),
    ])

    background = np.median(corners)

    # Pixels sufficiently different from the background
    content = np.abs(pixels - background) > threshold

    return np.count_nonzero(content) / content.size >= min_fraction


def is_landscape(image: Image.Image) -> bool:
    image_ratio = image.size[0] / image.size[1]
    if image_ratio > 1:
        return True
    return False


def export_image(image: Image.Image, output_path: Path) -> Path:
    if output_path.suffix == '.png':
        image.save(output_path, optimize=True)
    else:
        image.convert('L').save(output_path, quality=80, optimize=True)
    return output_path


def process_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    if image.mode != 'L':
        image = image.convert('L')

    if not has_content(image):
        raise ValueError(f"{image} doesn't seem to hold any content")

    # check orientation for double pages
    if is_landscape(image):
        image = image.rotate(-90, expand=True,
                             resample=Image.Resampling.NEAREST)

    image = simple_crop(image, padding=0)

    image = smart_resize(image, size, max_deform=10)

    image = image.quantize(colors=16, method=Image.Quantize.MEDIANCUT)

    return image


def run_image_processing(input_path: Path, output_path: Path, size: tuple[int, int]) -> list[Path]:
    if input_path.suffix not in SUPPORTED_IMAGES:
        raise NotImplementedError(
            f'File type not supported: {input_path.suffix}')

    with Image.open(input_path) as image:
        # Run Processing
        image = process_image(image, size)
        output_path = export_image(image, output_path)

    return output_path


def process_ebook(book: Ebook, device: Device, workspace: Path, image_workers: int, page_processor: Callable[[Path, Path], Path]) -> Ebook:
    # Processing
    # if 'mobi' in formats:
    cover_path = book.cover.uri

    processed_cover = None
    with Image.open(cover_path) as cover:
        cover = process_image(cover, device.resolution)
        cover_path = (workspace / "cover").with_suffix('.jpg')
        cover.convert('L').save(cover_path)
        processed_cover = Page(
            uri=cover_path,
            number=0,
            title=book.cover.title
        )
    image_paths = [
        page.uri
        for page in book.pages
    ]
    processed = []
    with ThreadPoolExecutor(max_workers=image_workers) as executor:
        futures = [
            executor.submit(page_processor, image_path,
                            workspace / (image_path.stem + '.png'), device.resolution)
            for image_path in image_paths
        ]

        for future in as_completed(futures):
            try:
                image_path = future.result()
            except Exception as e:
                print(e)
                continue
            else:
                processed.append(image_path)
    processed = sorted(processed, key=lambda path: path.stem)

    processed_pages = [
        Page(
            uri=path,
            number=index+1,
            title=book.pages[index].title
        )
        for index, path in enumerate(processed)
    ]

    return Ebook.from_book(book, cover=processed_cover, pages=processed_pages)


def export(processed_tome, device, formats, workdir, output_dir):
    # todo: remove workdir dependency
    if 'cbz' in formats:
        CBZExporter().export(processed_tome, device, output_dir)
    if 'epub' in formats or 'mobi' in formats:
        destination = output_dir if 'epub' in formats else workdir
        epub_path = EpubExporter().export(processed_tome, device, destination)

        if 'mobi' in formats:
            mobi_path = MobiExporter().export(processed_tome, device, epub_path)
            if 'epub' not in formats:
                move(mobi_path, output_dir.joinpath(mobi_path.name))


def run(tome: Ebook,
        device: Device,
        output_dir: Path,
        formats: list[str],
        workers: int
        ):

    with TemporaryDirectory(prefix='image-batch-') as tempdir:
        workdir = Path(tempdir)
        processed_tome = process_ebook(
            tome, device, workdir, workers, page_processor=run_image_processing)
        export(processed_tome, device, formats, workdir, output_dir)


def main(
    tomes: list[Ebook],
    device: Device,
    output_dir: Path,
    formats: list[str],
    image_workers: int,
    tome_workers: int
) -> None:
    print(f"Target device is {device.alias}")

    with ThreadPoolExecutor(max_workers=tome_workers) as executor:
        tome_promises = [
            executor.submit(run, tome, device,
                            output_dir, formats,
                            image_workers)
            for tome in tomes
        ]

        for promise in as_completed(tome_promises):
            try:
                promise.result()
            except Exception as e:
                print(e)
                continue
            else:
                print("Tome processing complete.")
