from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from manga_optimizer.constants import WRITING_MODE_ALIASES
from manga_optimizer.model.device import Device
from manga_optimizer.model.ebook import Ebook


class CBZExporter:
    suffix: str = '.cbz'

    def export(self, book: Ebook, device: Device, destination: Path) -> Path:
        filepath = destination / (book.title + self.suffix)
        pages = book.pages[::-
                           1] if book.writing_mode == WRITING_MODE_ALIASES['rl'] else book.pages
        with ZipFile(filepath, 'w', compression=ZIP_DEFLATED) as archive:
            archive.write(book.cover.uri)
            for page in pages:
                archive.write(page.uri)

        print(f'CBZ EXPORT TO: {filepath}')
        return filepath
