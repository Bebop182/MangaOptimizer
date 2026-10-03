import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from shutil import move
from tempfile import TemporaryDirectory

from PIL import Image

from manga_optimizer.image_processing import process_image

from .constants import SUPPORTED_IMAGES
from .export.cbz import CBZExporter
from .export.epub import EpubExporter
from .export.mobi import MobiExporter
from .model.device import Device
from .model.ebook import Ebook, Page

# Todo:
# Support epub page direction metadata
# Anti-rainbow effect for colored eink using fourier transforms
# improve test coverage
# implement progress logging

logger = logging.getLogger(__name__)


def export_image(image: Image.Image, output_path: Path) -> Path:
    if output_path.suffix == '.png':
        image.save(output_path, optimize=True)
    else:
        image.convert('L').save(output_path, quality=80, optimize=True)
    return output_path


def run_image_processing(input_path: Path, output_path: Path, size: tuple[int, int]) -> list[Path]:
    if input_path.suffix not in SUPPORTED_IMAGES:
        raise NotImplementedError(
            f'File type not supported: {input_path.suffix}')

    logger.debug(f"processing {input_path.stem}...")

    with Image.open(input_path) as image:
        # Run Processing
        image = process_image(image, target_size=size)
        output_path = export_image(image, output_path)

    logger.debug(f"{input_path.name} done.")

    return output_path


def process_tome(tome: Ebook, device: Device, workspace: Path, image_workers: int, page_processor: Callable[[Path, Path], Path]) -> Ebook:
    cover_path = tome.cover.uri

    processed_cover = None
    with Image.open(cover_path) as cover:
        cover = process_image(cover, device.resolution, quantize=False)
        cover_path = (workspace / "cover").with_suffix('.jpg')
        cover.save(cover_path)
        processed_cover = Page(
            uri=cover_path,
            number=0,
            title=tome.cover.title
        )
    image_paths = [
        page.uri
        for page in tome.pages
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
            except BaseException as e:  # noqa: BLE001
                logger.warning(e)
                continue
            else:
                processed.append(image_path)
    processed = sorted(processed, key=lambda path: path.stem)

    processed_pages = [
        Page(
            uri=path,
            number=index+1,
            title=tome.pages[index].title
        )
        for index, path in enumerate(processed)
    ]

    return Ebook.from_book(tome, cover=processed_cover, pages=processed_pages)


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
        ) -> Ebook:
    logger.info(f"Processing {tome.title}...")
    with TemporaryDirectory(prefix="image-batch-") as tempdir:
        workdir = Path(tempdir)
        processed_tome = process_tome(
            tome, device, workdir, workers, page_processor=run_image_processing)
        logger.info(
            f"{tome.title} is ready.\n Exporting...")
        export(processed_tome, device, formats, workdir, output_dir)
        logger.info(f"{tome.title} export has been completed.")
        return processed_tome


def main(
    tomes: list[Ebook],
    device: Device,
    output_dir: Path,
    formats: list[str],
    image_workers: int,
    tome_workers: int
) -> None:
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
            except BaseException as e:  # noqa: BLE001
                logger.warning(e)
                continue
            # else:
            #     logger.info(f"{tome.title} done.")
