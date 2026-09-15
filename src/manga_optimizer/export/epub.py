from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4
from io import BytesIO
from importlib.resources import files
from string import Template
from html import escape

from PIL import Image
from ebooklib import epub


def pngs_to_epub(
    image_paths: Iterable[Path],
    output_path: Path,
    design_size: tuple[int, int],
    *,
    lang: str = 'en',
    writing_mode: str = 'horizontal-rl',
    orientation: str = 'portrait'
) -> None:

    if not image_paths:
        raise ValueError('No PNG files found')

    width, height = design_size
    title = output_path.stem

    book = bootstrap_epub(title, design_size, lang, writing_mode, orientation)

    # Use the first image as the cover.
    cover_path = image_paths[0]
    cover_filename = Path('images/cover').with_suffix('.jpg')

    book.set_cover(str(cover_filename),
                   cover_path.read_bytes(), create_page=True)
    pages = []

    reset = epub.EpubItem(
        uid='css_reset',
        file_name='styles/reset.css',
        media_type='text/css',
        content=loadCSSReset()
    )
    book.add_item(reset)

    style = epub.EpubItem(
        uid='page_style',
        file_name='styles/page.css',
        media_type='text/css',
        content=loadPageStyle()
    )
    book.add_item(style)

    for index, image_path in enumerate(image_paths[1:], start=1):
        image_filename = f'images/page_{index}{image_path.suffix}'
        page_filename = f'page_{index}.xhtml'

        image = epub.EpubItem(
            uid=f'image_{index}',
            file_name=image_filename,
            media_type='image/png',
            content=image_path.read_bytes(),
        )
        book.add_item(image)

        page = epub.EpubHtml(
            uid=f'page_{index}',
            title=f'Page {index}',
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
            index, image_filename, width, height))
        # page.content = get_page_template(index, image_filename, width, height)

        book.add_item(page)
        pages.append(page)

    book.spine = pages

    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    book.toc = tuple(
        epub.Link(page.file_name, page.title, f'page_{i}')
        for i, page in enumerate(pages, start=1)
    )

    epub.write_epub(output_path, book)


def getBookIdentifier(title: str):
    return f'urn:uuid:{uuid4()}'


def bootstrap_epub(title: str, design_size: tuple[int, int],
                   lang: str = 'en',
                   writing_mode: str = 'lr',
                   orientation: str = 'portrait'
                   ):
    book = epub.EpubBook()
    book.set_identifier(getBookIdentifier(title))
    book.set_title(title)
    book.set_language(lang)

    book.add_metadata(namespace="rendition",
                      name="layout", value="pre-paginated")
    book.add_metadata(namespace="rendition", name="spread", value="none")
    book.add_metadata(namespace="rendition",
                      name="orientation", value=orientation)

    # Mobi requirement
    book.add_metadata(namespace=None, value=None,
                      name='meta',
                      others={
                          'name': 'original-resolution',
                          'content': f'{design_size[0]}x{design_size[1]}'
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
    index: int,
    image_filename: str,
    width: int,
    height: int,
) -> str:
    template = Template(
        files("manga_optimizer.export").joinpath(
            'page_template.xhtml').read_text(encoding="utf-8")
    )

    html = template.substitute(
        index=escape(str(index)),
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
