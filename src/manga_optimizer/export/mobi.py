from shutil import which
from pathlib import Path
import subprocess
import struct
import hashlib
import base64
import os

from ..model.ebook import Ebook
from ..model.device import Device

from mobi_header import MobiHeader


class MobiExporter:
    suffix: str = '.mobi'

    def export(self, book: Ebook, device: Device, destination: Path):
        epub_path = destination
        if destination.is_dir():
            epub_path = (destination/book.title).with_suffix(".epub")
        if epub_path.exists():
            epub_to_mobi(book, epub_path)
        else:
            print(f"MobiExporter Error: Could not locate {epub_path}")


def make_id(seed: str) -> str:
    digest = hashlib.sha256(
        seed.strip().lower().encode("utf-8")
    ).digest()

    encoded = base64.b32encode(digest).decode("ascii")
    return 'B1' + str(encoded[:8])


def epub_to_mobi(book: Ebook, epub: Path):
    kindlegen = os.getenv('KINDLEGEN')
    if not kindlegen:
        kindlegen = which("kindlegen")
    if kindlegen is None:
        raise RuntimeError(
            "kindlegen is required. Install it and ensure it is on PATH."
        )

    # kindlegen_cmd = [
    #     kindlegen,
    #     epub,
    #     '-dont_append-source',
    # ]
    kindlegen_cmd = f'{kindlegen} "{epub}" -dont_append_source'

    try:
        result = subprocess.run(
            kindlegen_cmd,
            check=True,
            text=True,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        print(result.stdout)
    except subprocess.CalledProcessError as error:
        print(f"kindlegen failed with exit code {error.returncode}")
        print(error.stdout)
    else:
        mobi_path = epub.with_suffix(".mobi")
        metadatas = [
            (113, book.uid),
            (501, "PDOC")
        ]
        set_exth(mobi_path, metadatas)
        return mobi_path
    return None


def set_exth(mobi_path: Path, metadatas: list[tuple[int, str]]):
    header = MobiHeader(mobi_path)
    for index, value in metadatas:
        header.add_exth_record(
            index,
            value,
            str)
    header.to_file()
