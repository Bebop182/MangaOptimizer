import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor, as_completed
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image
import numpy as np
from .export.epub import pngs_to_epub
# from rainbowEffectEraser import erase_rainbow_artifacts

# DISPLAY_RES = (1072, 1448) #Kobo Clara Color
DISPLAY_RES = (600, 800) # Kindle 8th Basic
DISPLAY_RATIO = DISPLAY_RES[0] / DISPLAY_RES[1]
SUPPORTED_IMAGES = {'.png', '.jpg', '.jpeg', '.webp'}
FLOW_DIRECTION = ('lr', 'rl')
OUTPUT_FORMATS = ('cbz', 'epub', 'pdf')


def process_image(image:Image.Image) -> Image.Image:
    if image.mode != 'L':
        image = image.convert('L')

    if not has_content(image):
        raise ValueError(f"{image} doesn't seem to hold any content")

    # check orientation for double pages
    if is_landscape(image):
        image = image.rotate(-90, expand=True, resample=Image.Resampling.NEAREST)

    image = simple_crop(image, padding=0)
    
    image = smart_resize(image, max_deform=10)

    image = image.quantize(colors=16, method=Image.Quantize.MEDIANCUT)

    return image

def has_content(image, threshold=12, min_fraction=0.001):
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

def image_job(image_path : Path, output_dir: Path) -> tuple[str, Path]:
    output_format = 'png'
    if image_path.suffix not in SUPPORTED_IMAGES:
        raise NotImplementedError(f'File type not supported: {image_path.suffix}')

    with Image.open(image_path) as image:
        # Run Processing
        image = process_image(image)

        if output_format == 'png':
            processed_name = f'{image_path.stem}.png'
            processed_path = output_dir.joinpath(processed_name)
            image.save(processed_path, optimize=True)
        else:
            processed_name = f'{image_path.stem}.jpg'
            processed_path = output_dir.joinpath(processed_name)
            image.convert('L').save(processed_path, quality=80, optimize=True)

    return processed_name, processed_path

def images_from_dir(directory : Path):
    return [
        image_path
        for image_path in directory.iterdir()
        if image_path.is_file() and image_path.suffix.lower() in SUPPORTED_IMAGES
    ]

def is_landscape(image:Image.Image):
    image_ratio = image.size[0] / image.size[1]
    if image_ratio > 1:
        return True
    return False

def exportCBZ(images: tuple[str, Path], filename, directory: Path):
    cbz_path = directory.joinpath(filename)
    with ZipFile(cbz_path, 'w', compression=ZIP_DEFLATED) as archive:
        for image in images:
            name, path = image
            archive.write(path, arcname=name)
    print(cbz_path)

def exportEPUB(images: tuple [str, Path], filename, directory: Path, flow_direction: str):
    paths = [
        path
        for _,path in sorted(images, key=lambda image: image[0])
    ]
    epub = directory.joinpath(filename)
    pngs_to_epub(paths, epub, DISPLAY_RES, flow_direction=flow_direction)
    print(epub)

def exportPDF(images: tuple[str, Path], filename, directory: Path):
    pages = [
        Image.open(path)
        for _,path in sorted(images, key=lambda image: image[0])
    ]

    pdf_path = directory.joinpath(filename)
    pages[0].save(
        pdf_path,
        append_images=pages[1:],
        resolution=167,
    )
    print(pdf_path)

# def exportMOBI(images: tuple[str, Path], filename, directory: Path):
#     paths = [
#         path
#         for _,path in sorted(images, key=lambda image: image[0])
#     ]
#     mobi = directory.joinpath(filename)
#     pngs_to_mobi(paths, mobi, title=filename)

def main(input_path: Path, output_path: Path, formats: list[str], flow_direction: str, worker_count: int) -> None:

    image_paths = images_from_dir(input_path)
    processed = []
    
    with (
        TemporaryDirectory(prefix='image-batch-') as directory,
        ThreadPoolExecutor(max_workers=worker_count) as executor
    ):
        temp_dir = Path(directory)

        futures = [
            executor.submit(image_job, image_path, temp_dir)
            for image_path in image_paths
        ]

        for future in as_completed(futures):
            try:
                image_name, image_path = future.result()
            except Exception as e:
                print(e)
                continue
            else:
                processed.append(
                    (image_name, image_path)
                )
        for ext in formats:
            match ext:
                case 'cbz':
                    exportCBZ(processed, f'{input_path.name}.cbz', output_path)
                case 'epub':
                    exportEPUB(images=processed, filename=f'{input_path.name}.epub', directory=output_path, flow_direction=flow_direction)
                case 'pdf':
                    exportPDF(processed, f'{input_path.name}.pdf', output_path)
                case _:
                    print('no valid export format found')

