import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def page_crop(
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

    content_per_row = content.sum(axis=1)
    content_per_column = content.sum(axis=0)

    row_ratio = content_per_row / width
    column_ratio = content_per_column / height

    min_content_ratio = 0.03
    valid_rows = row_ratio >= min_content_ratio
    valid_columns = column_ratio >= min_content_ratio

    # mask line and column with too few content pixels
    content[~valid_rows, :] = False
    content[:, ~valid_columns] = False

    ys, xs = np.where(content)

    if len(xs) == 0:
        raise ValueError("No content detected")

    left = max(0, int(xs.min()) - padding)
    top = max(0, int(ys.min()) - padding)
    right = min(width, int(xs.max()) + padding + 1)
    bottom = min(height, int(ys.max()) + padding + 1)

    x_croppedratio = (left + width - right) / width
    y_croppedratio = (top + height - bottom) / height

    # cancel crop if the page is mostly empty to avoid losing framing of small elements
    if x_croppedratio >= 0.2 and y_croppedratio >= 0.2:
        return image

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


def is_landscape(image: Image.Image) -> bool:
    image_ratio = image.size[0] / image.size[1]
    return image_ratio > 1


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


def process_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image_name = Path(image.filename).stem

    if image.mode != 'L':
        image = image.convert('L')

    if not has_content(image):
        raise ValueError(f"{image_name} doesn't seem to hold any content")

    # check orientation for double pages
    if is_landscape(image):
        logger.debug(f"\trotating {image_name}")
        image = image.rotate(-90, expand=True,
                             resample=Image.Resampling.NEAREST)
    og_size = image.size
    image = page_crop(image, padding=0)
    logger.debug(
        f"\t{image_name} cropped to {image.size} from {og_size}")

    image = smart_resize(image, size, max_deform=10)
    logger.debug(f"\t{image_name} resized to {image.size}")

    image = image.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    logger.debug(f"\t{image_name} quantized to 16 shades")

    return image
