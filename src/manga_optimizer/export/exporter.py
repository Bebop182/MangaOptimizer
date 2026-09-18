from pathlib import Path
from typing import Protocol

from manga_optimizer.model.ebook import Ebook
from ..model.device import Device


class EbookExporter(Protocol):
    suffix: str

    def export(self, book: Ebook, device: Device, destination: Path) -> Path:
        ...
