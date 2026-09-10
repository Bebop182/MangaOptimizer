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
    cover_filename = Path('images/cover').with_suffix('.jpg')

    book.set_cover(str(cover_filename), cover_path.read_bytes(), create_page=True)
    pages = []

    reset = epub.EpubItem(
        uid='css_reset',
        file_name='styles/reset.css',
        media_type='text/css',
        content=getCSSReset()
    )
    book.add_item(reset) 

    style = epub.EpubItem(
        uid='page_style',
        file_name='styles/page.css',
        media_type='text/css',
        content=getPageStyle()
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
        page.set_content(get_page_template(index, image_filename, width, height))
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
    lang:str = 'en', 
    writing_mode: str = 'lr',
    orientation: str = 'portrait'
    ):
    book = epub.EpubBook()
    book.set_identifier(getBookIdentifier(title))
    book.set_title(title)
    book.set_language(lang)

    book.add_metadata(namespace="rendition", name="layout", value="pre-paginated")
    book.add_metadata(namespace="rendition", name="spread", value="none")
    book.add_metadata(namespace="rendition", name="orientation", value=orientation)

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
</head>
<body>
    <img src="{image_filename}" alt="Page {index}" width=auto height=100%/>
</body>
</html>
'''

def getPageStyle():
    return b'''
html,body {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
}
body {
    position: relative;
}
img {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    width: auto;
    object-fit: contain;
    object-position: center;
}
'''

def getCSSReset():
    return b'''
/* EPUB 2/3 and Kindle-compatible CSS reset */

/* Box sizing */
html {
  margin: 0;
  padding: 0;
}

body,
div,
section,
article,
aside,
header,
footer,
nav,
main,
figure,
figcaption,
p,
blockquote,
pre,
h1,
h2,
h3,
h4,
h5,
h6,
ul,
ol,
li,
dl,
dt,
dd,
table,
thead,
tbody,
tfoot,
tr,
th,
td,
img,
a,
em,
strong,
small,
sub,
sup,
hr {
  margin: 0;
  padding: 0;
}

/* Base document */
body {
  background: transparent;
  color: #000;
  font-family: serif;
  font-size: 1em;
  font-style: normal;
  font-weight: normal;
  line-height: 1.4;
  text-align: left;
  text-indent: 0;
}

/* Headings */
h1,
h2,
h3,
h4,
h5,
h6 {
  font-family: sans-serif;
  font-style: normal;
  font-weight: bold;
  line-height: 1.2;
  text-align: left;
  text-indent: 0;
}

/* Paragraphs */
p {
  text-align: left;
  text-indent: 1.5em;
}

p:first-child,
h1 + p,
h2 + p,
h3 + p,
h4 + p,
h5 + p,
h6 + p,
blockquote + p,
figure + p {
  text-indent: 0;
}

/* Links */
a {
  color: inherit;
  text-decoration: underline;
}

/* Emphasis */
em,
i {
  font-style: italic;
}

strong,
b {
  font-weight: bold;
}

/* Lists */
ul,
ol {
  margin-left: 2em;
}

li {
  margin: 0;
  padding: 0;
}

/* Block quotes */
blockquote {
  margin: 1em 2em;
  padding: 0;
  font-style: italic;
}

/* Preformatted text */
pre,
code,
kbd,
samp {
  font-family: monospace;
  font-size: 0.9em;
}

/* Images and figures */
img {
  border: 0;
  width: auto;
  height: auto;
}

figure {
  text-align: center;
}

figcaption {
  text-align: center;
  font-size: 0.9em;
}

/* Tables */
table {
  border-collapse: collapse;
  border-spacing: 0;
  width: 100%;
}

th,
td {
  text-align: left;
  vertical-align: top;
}

/* Rules */
hr {
  border: 0;
  border-top: 1px solid #000;
  height: 0;
  margin: 1em 0;
}

/* Avoid forced page behavior from browser defaults */
section,
article,
div {
  page-break-before: auto;
  page-break-after: auto;
}
'''
