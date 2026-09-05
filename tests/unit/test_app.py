from manga_optimizer import app

from pytest import fail
from os import getcwd
from pathlib import Path
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
    assert len(images) == 5

def test_exportCBZ(tmp_path: Path):
    images = app.images_from_dir(TEST_BOOK)
    ebook_path = tmp_path / (TEST_BOOK.stem+'.cbz')
    app.exportCBZ(images, ebook_path)

    assert ebook_path.exists()
    assert ebook_path.is_file()

def test_exportEPUB(tmp_path: Path):
    images = app.images_from_dir(TEST_BOOK)
    ebook_path = tmp_path / (TEST_BOOK.stem+'.epub')
    app.exportEPUB(images, ebook_path)

    assert ebook_path.exists()
    assert ebook_path.is_file()

def test_exportPDF(tmp_path: Path):
    images = app.images_from_dir(TEST_BOOK)
    ebook_path = tmp_path / (TEST_BOOK.stem+'.pdf')
    app.exportPDF(images, ebook_path)
    
    assert ebook_path.exists()
    assert ebook_path.is_file()
