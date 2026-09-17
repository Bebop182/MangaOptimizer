from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path
from uuid import uuid4
from io import BytesIO
from string import Template
from html import escape

from ..model.ebook import Ebook
from ..model.device import Device

from PIL import Image
from ebooklib import epub


class EpubExporter:
    suffix: str = '.epub'

    def export(self, book: Ebook, device: Device, destination: Path):
        image_paths = [
            page.uri
            for page in book.pages
        ]

        pngs_to_epub(
            book,
            device,
            filepath=destination/(book.title+self.suffix)
        )


def pngs_to_epub(
    book: Ebook,
    device: Device,
    filepath: Path,
) -> None:

    image_paths = [
        page.uri
        for page in book.pages
    ]

    if not image_paths:
        raise ValueError('No PNG files found')

    width, height = device.resolution

    epubBook = bootstrap_epub(book.uid, book.title, device.resolution, book.language,
                              book.writing_mode, book.orientation)
    cover_suffix = Path(book.cover.uri).suffix
    epubBook.set_cover(book.cover.title+cover_suffix,
                       book.cover.uri.read_bytes(), create_page=True)
    pages = []

    reset = epub.EpubItem(
        uid='css_reset',
        file_name='styles/reset.css',
        media_type='text/css',
        content=loadCSSReset()
    )
    epubBook.add_item(reset)

    style = epub.EpubItem(
        uid='page_style',
        file_name='styles/page.css',
        media_type='text/css',
        content=loadPageStyle()
    )
    epubBook.add_item(style)

    lang = book.language
    width, height = device.resolution
    for image_page in book.pages:
        image_filename = f'images/{image_page.title}{image_page.uri.suffix}'
        page_filename = f'{image_page.title}.xhtml'

        image = epub.EpubItem(
            uid=f'image_{image_page.number}',
            file_name=image_filename,
            media_type='image/png',
            content=image_page.uri.read_bytes(),
        )
        epubBook.add_item(image)

        page = epub.EpubHtml(
            uid=image_page.title,
            title=image_page.title,
            file_name=page_filename,
            lang=lang,
        )
        page.add_meta(
            name='viewport',
            content=f'width={width},height={height}',
        )
        page.add_link(
            href='styles/reset.css',
            rel='stylesheet',
            type='text/css',
        )
        page.add_link(
            href='styles/page.css',
            rel='stylesheet',
            type='text/css',
        )
        page.set_content(load_page_template(
            image_page.number, image_filename, width, height))

        epubBook.add_item(page)
        pages.append(page)

    epubBook.spine = pages

    epubBook.add_item(epub.EpubNav())
    epubBook.add_item(epub.EpubNcx())

    epubBook.toc = tuple(
        epub.Link(page.file_name, page.title, page.id)
        for page in pages
    )

    print(f'EPUB EXPORT TO: {filepath}')

    epub.write_epub(filepath, epubBook)


def bootstrap_epub(uid: str, title: str, design_size: tuple[int, int],
                   lang: str,
                   writing_mode: str,
                   orientation: str,
                   ):
    book = epub.EpubBook()
    book.set_identifier(uid)
    book.set_title(title)
    book.set_language(lang)

    book.add_metadata(namespace="rendition",
                      name="layout", value="pre-paginated")
    book.add_metadata(namespace="rendition", name="spread", value="none")
    book.add_metadata(namespace="rendition",
                      name="orientation", value=orientation)

    # Mobi requirement
    width, height = design_size
    book.add_metadata(namespace=None, value=None,
                      name='meta',
                      others={
                          'name': 'original-resolution',
                          'content': f'{width}x{height}'
                      }
                      )

    # <meta name='primary-writing-mode' content='horizontal-rl'/>
    # Valid values are horizontal-lr, horizontal-rl, vertical-lr, and vertical-rl
    # default horizontal-lr
    book.add_metadata(namespace=None, value=None,
                      name='meta',
                      others={
                          'name': 'primary-writing-mode',
                          'content': f'{writing_mode}'
                      }
                      )

    return book


def load_page_template(
    number: int,
    image_filename: str,
    width: int,
    height: int,
) -> str:
    template = Template(
        files("manga_optimizer.export").joinpath(
            'page_template.xhtml').read_text(encoding="utf-8")
    )

    html = template.substitute(
        number=escape(str(number)),
        filename=escape(str(image_filename), quote=True),
    )
    return html


def loadPageStyle():
    css = files("manga_optimizer.export").joinpath(
        'page.css').read_text(encoding="utf-8")
    return css


def loadCSSReset():
    css = files("manga_optimizer.export").joinpath(
        'reset.css').read_text(encoding="utf-8")
    return css
