from shutil import which
from pathlib import Path
import subprocess
import struct
import os

from mobi_header import MobiHeader

import hashlib
import base64


def make_id(seed: str) -> str:
    digest = hashlib.sha256(
        seed.strip().lower().encode("utf-8")
    ).digest()

    encoded = base64.b32encode(digest).decode("ascii")
    return 'B1' + str(encoded[:8])


def epub_to_mobi(epub: Path):
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
    else:
        mobi_path = epub.with_suffix('.mobi')
        metadatas = [
            (113, make_id(mobi_path.stem)),
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
