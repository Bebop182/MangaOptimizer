from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4
from io import BytesIO

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
    cover_filename = Path('images/cover').with_suffix(cover_path.suffix)

    book.set_cover(str(cover_filename), cover_path.read_bytes())

    pages = []

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

        page.content = get_page_template(index, image_filename, width, height)

        book.add_item(page)
        pages.append(page)

    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    book.toc = tuple(
        epub.Link(page.file_name, page.title, f'page_{i}')
        for i, page in enumerate(pages, start=1)
    )

    book.spine = pages
    epub.write_epub(output_path, book)

def getBookIdentifier(title: str):
    return f'urn:uuid:{uuid4()}'

def bootstrap_epub(title: str, design_size: tuple[int, int], 
    lang:str='en', 
    writing_mode: str = 'lr',
    orientation: str = 'portrait'
    ):
    book = epub.EpubBook()
    book.set_identifier(getBookIdentifier(title))
    book.set_title(title)
    book.set_language(lang)


    book.add_metadata(namespace="rendition", name="layout", value="pre-paginated")
    book.add_metadata(namespace="rendition", name="spread", value="none")
    book.add_metadata(namespace="rendition", name=orientation, value="portrait")

    # Mobi requirement
    book.add_metadata(namespace=None, value=None,
        name='meta', 
        others={
            'name': 'originial-resolution',
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

def get_page_template(
    index: int,
    image_filename: str,
    width: int,
    height: int,
) -> str:
    return f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Page {index}</title>
  <meta name="viewport" content="width={width},height={height}" />
  
</head>
<body>
  <img src="{image_filename}" alt="Page {index}" />
</body>
</html>
'''
