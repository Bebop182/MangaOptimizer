from manga_optimizer import app

import time
import random
from os import getcwd
from pathlib import Path
from pytest import fail

from PIL import Image

ROOT = Path(getcwd())
TESTS = ROOT / 'tests'
TEST_BOOK = TESTS / 'data' / 'TestBook'

def test_is_landscape():
    landscape_image = Image.open(TEST_BOOK / 'berserk-t105.jpg')
    assert app.is_landscape(landscape_image) == True

    portrait_image = Image.open(TEST_BOOK / 'berserk-t104.jpg')
    assert app.is_landscape(portrait_image) == False

def test_simple_crop():
    fail('not implemented')
    
def test_smart_resize():
    fail('not implemented')

def test_has_content():
    image_white = Image.new('L', (600, 800), "white")
    assert app.has_content(image_white) == False

    image_black = Image.new('L', (600, 800), "black")
    assert app.has_content(image_black) == False

    image_black = Image.new('L', (600, 800), 125)
    assert app.has_content(image_black) == False

    content_image = Image.open(TEST_BOOK / 'berserk-t104.jpg')
    assert app.has_content(content_image) == True

def test_images_from_dir():
    images = app.images_from_dir(TEST_BOOK)
    assert len(images) == 7

def test_process_batch():
    root = Path('path') / 'to' / 'images'
    input_paths = [
        root / 'image_001.jpg',
        root / 'image_002.jpg',
        root / 'image_003.jpg',
        root / 'image_004.jpg',
        root / 'image_005.jpg',
        root / 'image_006.jpg',
        root / 'image_007.jpg',
        root / 'image_008.jpg',
        root / 'image_009.jpg',
    ]

    # seed 42
    rng = random.Random(42)
    input_delays = {
        path.stem: rng.uniform(0.01, 0.05)
        for path in input_paths
    }
    
    def fake_process(input_file: Path, output_file: Path) -> list[Path]:
        delay = input_delays[input_file.stem]
        time.sleep(delay)
        return output_file

    output_dir = Path('temp')
    processed = app.process_batch(
        input_paths,
        fake_process,
        output_dir,
        worker_count=7
        )
    processed = [
        image_path.stem
        for image_path in processed
    ]

    expected = [
        image_path.stem
        for image_path in input_paths
    ]
    assert processed == expected


def test_exportCBZ(tmp_path: Path):
    images = app.images_from_dir(TEST_BOOK)
    ebook_path = tmp_path / (TEST_BOOK.stem + '.cbz')
    app.exportCBZ(images, ebook_path)

    assert ebook_path.exists()
    assert ebook_path.is_file()


def test_exportEPUB(tmp_path: Path):
    images = app.images_from_dir(TEST_BOOK)
    ebook_path = tmp_path / (TEST_BOOK.stem + '.epub')
    app.exportEPUB(images, ebook_path)

    assert ebook_path.exists()
    assert ebook_path.is_file()


def test_exportPDF(tmp_path: Path):
    images = app.images_from_dir(TEST_BOOK)
    ebook_path = tmp_path / (TEST_BOOK.stem + '.pdf')
    app.exportPDF(images, ebook_path)
    
    assert ebook_path.exists()
    assert ebook_path.is_file()
