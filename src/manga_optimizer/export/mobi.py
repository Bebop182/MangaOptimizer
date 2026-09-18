from shutil import which
from pathlib import Path
import subprocess
import struct
import hashlib
import base64
import os

from ..model.ebook import Ebook
from ..model.device import Device


class MobiExporter:
    suffix: str = '.mobi'

    def export(self, book: Ebook, device: Device, destination: Path) -> Path:
        epub_path = destination
        mobi_path = None
        if destination.is_dir():
            epub_path = (destination/book.title).with_suffix(".epub")
        if not epub_path.is_file():
            print(
                f"MobiExporter Error: Could not locate {epub_path} Is file?{epub_path.is_file()}")
            return None

        mobi_path = epub_to_mobi(book, epub_path)
        print(mobi_path)
        return mobi_path


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
    #     "-dont_append_source",
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
        # metadatas = [
        #     (113, book.uid),
        #     (501, "PDOC")
        # ]
        # # set_exth(mobi_path, metadatas)
        # print_exth(mobi_path)
        return mobi_path
    return None
