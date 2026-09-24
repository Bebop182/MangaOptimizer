from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4
from io import BytesIO
from string import Template
from html import escape
from importlib import resources

from ..model.ebook import Ebook
from ..model.device import Device

from PIL import Image
from ebooklib import epub

RESOURCES_PATH = resources.files("manga_optimizer") / "resources"


class EpubExporter:
    suffix: str = '.epub'

    def export(self, book: Ebook, device: Device, destination: Path) -> Path:
        image_paths = [
            page.uri
            for page in book.pages
        ]
        filepath = destination/(book.title+self.suffix)
        pngs_to_epub(
            book,
            device,
            filepath=filepath
        )
        print(f'EPUB EXPORT TO: {filepath}')
        return filepath


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

    document = bootstrap_epub(book, device)
    cover_suffix = Path(book.cover.uri).suffix
    document.set_cover(book.cover.title+cover_suffix,
                       book.cover.uri.read_bytes(), create_page=True)
    pages = []

    # reset = epub.EpubItem(
    #     uid='css_reset',
    #     file_name='styles/reset.css',
    #     media_type='text/css',
    #     content=loadCSSReset()
    # )
    # epubBook.add_item(reset)

    # style = epub.EpubItem(
    #     uid='page_style',
    #     file_name='styles/page.css',
    #     media_type='text/css',
    #     content=loadPageStyle()
    # )
    # epubBook.add_item(style)

    lang = book.language
    width, height = device.resolution
    for image_page in book.pages:
        image_filename = (
            f'images/{image_page.title}{image_page.uri.suffix}').replace(' ', '_')
        page_filename = (f'{image_page.title}.xhtml').replace(' ', '_')

        image = epub.EpubItem(
            uid=f'image_{image_page.number}',
            file_name=image_filename,
            media_type='image/png',
            content=image_page.uri.read_bytes(),
        )
        document.add_item(image)

        page = epub.EpubHtml(
            uid=image_page.title.lower().replace(' ', '_'),
            title=image_page.title,
            file_name=page_filename,
            lang=lang,
        )
        page.add_meta(
            name='viewport',
            content=f'width={width},height={height}',
        )
        # page.add_link(
        #     href='styles/reset.css',
        #     rel='stylesheet',
        #     type='text/css',
        # )
        # page.add_link(
        #     href='styles/page.css',
        #     rel='stylesheet',
        #     type='text/css',
        # )
        page.set_content(load_page_template(
            image_page.number, image_filename, width, height))

        document.add_item(page)
        pages.append(page)

    document.spine = pages
    # direction: Options are "ltr", "rtl" and "default"
    # document.direction =

    document.add_item(epub.EpubNav())
    document.add_item(epub.EpubNcx())

    document.toc = tuple(
        epub.Link(page.file_name, page.title, page.id)
        for page in pages
    )

    epub.write_epub(filepath, document)


def bootstrap_epub(book: Ebook, device: Device):
    uid = book.uid
    title = book.title
    lang = book.language
    writing_mode = book.writing_mode
    orientation = book.orientation
    width, height = device.resolution

    document = epub.EpubBook()
    document.set_identifier(uid)
    document.set_title(title)
    document.set_language(lang)

    document.add_metadata(namespace=None, name="meta", value="pre-paginated",
                          others={"property": "rendition:layout"})
    document.add_metadata(namespace=None, name="meta", value=orientation,
                          others={"property": "rendition:orientation"})
    document.add_metadata(namespace=None, name="meta", value="none",
                          others={"property": "rendition:spread"})

    # Mobi requirement
    document.add_metadata(namespace=None, name="meta", value=f"{width}x{height}",
                          others={"property": "original-resolution"})

    # <meta name='primary-writing-mode' content='horizontal-rl'/>
    # Valid values are horizontal-lr, horizontal-rl, vertical-lr, and vertical-rl
    # default horizontal-lr
    document.add_metadata(namespace=None, name="meta", value=writing_mode,
                          others={"property": "primary-writing-mode"})

    return document


def load_page_template(
    number: int,
    image_filename: str,
    width: int,
    height: int,
) -> str:
    template_path = RESOURCES_PATH / "page_template.xhtml"
    template = Template(
        template_path.read_text(encoding="utf-8")
    )

    html = template.substitute(
        number=escape(str(number)),
        filename=escape(str(image_filename), quote=True),
    )
    return html


def loadPageStyle():
    style_path = RESOURCES_PATH / "page.css"
    return style_path.read_text(encoding="utf-8")


def loadCSSReset():
    style_path = RESOURCES_PATH / "reset.css"
    return style_path.read_text(encoding="utf-8")
