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
from .model import ebook
from .model.device import Device

from PIL import Image
import numpy as np


# DISPLAY_RES = (1072, 1448) #Kobo Clara Color
DISPLAY_RES = (600, 800)  # Kindle 8th Basic
DISPLAY_RATIO = DISPLAY_RES[0] / DISPLAY_RES[1]
SUPPORTED_IMAGES = {'.png', '.jpg', '.jpeg', '.webp'}
FLOW_DIRECTION = ('lr', 'rl')
OUTPUT_FORMATS = ('cbz', 'epub', 'mobi', 'pdf')


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
    max_deform: int = 10
) -> Image.Image:

    display_ratio = DISPLAY_RATIO
    image_ratio = image.width / image.height
    tolerance = max_deform / 100

    if image_ratio > display_ratio:
        # L'image est relativement plus large.
        # On conserve la largeur et on modifie la hauteur.
        # width = pil_image.width
        width = DISPLAY_RES[0]
        reduction_factor = image.width / DISPLAY_RES[0]

        required_factor = image_ratio / display_ratio
        applied_factor = min(required_factor, 1.0 + tolerance)

        height = round(image.height * applied_factor / reduction_factor)
        height = min(DISPLAY_RES[1], height)

    else:
        # L'image est relativement plus haute.
        # On conserve la hauteur et on modifie la largeur.
        height = DISPLAY_RES[1]
        reduction_factor = image.height / DISPLAY_RES[1]

        required_factor = display_ratio / image_ratio
        applied_factor = min(required_factor, 1.0 + tolerance)

        width = round(image.width * applied_factor / reduction_factor)
        width = min(DISPLAY_RES[0], width)

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


def images_from_dir(directory: Path) -> list[Path]:
    image_paths = [
        image_path
        for image_path in directory.iterdir()
        if image_path.is_file() and image_path.suffix.lower() in SUPPORTED_IMAGES
    ]
    return sorted(image_paths, key=lambda path: path.stem)


def is_landscape(image: Image.Image) -> bool:
    image_ratio = image.size[0] / image.size[1]
    if image_ratio > 1:
        return True
    return False


def image_export(image: Image.Image, output_path: Path) -> Path:
    if output_path.suffix == '.png':
        image.save(output_path, optimize=True)
    else:
        image.convert('L').save(output_path, quality=80, optimize=True)
    return output_path


def process_image(image: Image.Image) -> Image.Image:
    if image.mode != 'L':
        image = image.convert('L')

    if not has_content(image):
        raise ValueError(f"{image} doesn't seem to hold any content")

    # check orientation for double pages
    if is_landscape(image):
        image = image.rotate(-90, expand=True,
                             resample=Image.Resampling.NEAREST)

    image = simple_crop(image, padding=0)

    image = smart_resize(image, max_deform=10)

    image = image.quantize(colors=16, method=Image.Quantize.MEDIANCUT)

    return image


def image_worker(input_path: Path, output_path: Path) -> list[Path]:
    if input_path.suffix not in SUPPORTED_IMAGES:
        raise NotImplementedError(
            f'File type not supported: {input_path.suffix}')

    with Image.open(input_path) as image:
        # Run Processing
        image = process_image(image)
        output_path = image_export(image, output_path)

    return output_path


def process_batch(
    image_paths: list[Path],
    processing_job: Callable[[Path, Path], Path],
    tmp_dir: Path,
    worker_count: int
) -> list[Path]:
    processed = []
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(processing_job, image_path,
                            tmp_dir / (image_path.stem + '.png'))
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
    # return processed
    return sorted(processed, key=lambda path: path.stem)


def exportCBZ(images: list[Path], file_path: Path):
    with ZipFile(file_path, 'w', compression=ZIP_DEFLATED) as archive:
        for image in images:
            archive.write(image)
    print(file_path)


def exportEPUB(images: list[Path], file_path: Path, flow_direction: str = 'horizontal-rl'):
    pngs_to_epub(images, file_path, DISPLAY_RES, writing_mode=flow_direction)
    print(file_path)


def exportMOBI(epub: Path):
    from .export.mobi import epub_to_mobi
    return epub_to_mobi(epub)


def exportPDF(images: list[Path], file_path: Path):
    pages = [
        Image.open(path)
        for path in sorted(images)
    ]

    pages[0].save(
        file_path,
        append_images=pages[1:],
        resolution=167,
    )
    print(file_path)


def process_ebook(book: ebook.Ebook, workspace: Path, worker_count: int) -> ebook.Ebook:
    # Processing
    # if 'mobi' in formats:
    cover_path = book.cover.uri

    processed_cover = None
    with Image.open(cover_path) as cover:
        cover = process_image(cover)
        cover_path = (workspace / "cover").with_suffix('.jpg')
        cover.convert('L').save(cover_path, dpi=(167, 167))
        processed_cover = ebook.Page(
            uri=cover_path,
            number=0,
            title=book.cover.title
        )
    image_paths = [
        page.uri
        for page in book.pages
    ]
    processed = process_batch(
        image_paths, image_worker, workspace, worker_count)
    # if cover_path != None:
    #     processed.insert(0, cover_path)
    processed_pages = [
        ebook.Page(
            uri=path,
            number=index+1,
            title=book.pages[index].title
        )
        for index, path in enumerate(processed)
    ]

    return ebook.Ebook.from_book(book, cover=processed_cover, pages=processed_pages)


def main(
    input_dir: Path,
    output_dir: Path,
    formats: list[str],
    flow_direction: str,
    worker_count: int,
    cover_path: Path = None
) -> None:

    # Construct ebook:
    from manga_optimizer.model import ebook

    image_paths = images_from_dir(input_dir)
    cover = ebook.Page(
        uri=image_paths[0],
        number=0,
        title="cover"
    )
    pages = [
        ebook.Page(
            uri=path,
            title=f'Page {number:03d}',
            number=number
        )
        for number, path in enumerate(image_paths[1:], start=1)
    ]
    book = ebook.Ebook(
        title=input_dir.stem,
        cover=cover,
        pages=pages
    )

    with TemporaryDirectory(prefix='image-batch-') as temp_dir:
        temp_dir = Path(temp_dir)

        processed_book = process_ebook(book, temp_dir, worker_count)

        device = Device(
            alias="k8", model="Kindle Basic 8th Gen", dpi=167, resolution=(600, 800)
        )

        if 'cbz' in formats:
            CBZExporter().export(processed_book, device, output_dir)

        if 'epub' in formats or 'mobi' in formats:
            destination = output_dir if 'epub' in formats else temp_dir
            epub_path = EpubExporter().export(processed_book, device, destination)

            if 'mobi' in formats:
                mobi_path = MobiExporter().export(processed_book, device, epub_path)
                if 'epub' not in formats:
                    move(mobi_path, output_dir.joinpath(mobi_path.name))
