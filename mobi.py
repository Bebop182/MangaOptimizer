import hashlib
import struct
import time
from pathlib import Path
from typing import Iterable


def _u16(value: int) -> bytes:
    return struct.pack(">H", value & 0xFFFF)


def _u32(value: int) -> bytes:
    return struct.pack(">I", value & 0xFFFFFFFF)


def _pdb_timestamp() -> int:
    return int(time.time()) + 2_082_844_800


def _pdb_header(name: str, record_count: int, uid: int) -> bytes:
    name_bytes = name.encode("ascii", "replace")[:31].ljust(32, b"\0")
    now = _pdb_timestamp()

    return b"".join(
        (
            name_bytes,
            _u16(0),                 # attributes
            _u16(0),                 # version
            _u32(now),               # creation time
            _u32(now),               # modification time
            _u32(0),                 # last backup time
            _u32(0),                 # modification number
            _u32(0),                 # app info offset
            _u32(0),                 # sort info offset
            b"BOOK",                 # database type
            b"MOBI",                 # creator
            _u32(uid),               # unique ID seed
            _u32(0),                 # next record list
            _u16(record_count),
        )
    )


def _palm_doc_header(text_length: int, record_count: int) -> bytes:
    return b"".join(
        (
            _u16(1),                 # no compression
            _u16(0),                 # unused
            _u32(text_length),
            _u16(record_count),
            _u16(4096),              # text record size
            _u16(0),                 # encryption
            _u16(0),                 # unused
        )
    )


def _mobi_header(
    *,
    uid: int,
    title_offset: int,
    title_length: int,
    first_image_record: int,
    text_record_count: int,
) -> bytes:
    header = bytearray(232)

    def put(offset: int, value: int) -> None:
        header[offset : offset + 4] = _u32(value)

    header[0:4] = b"MOBI"
    put(4, 232)                  # MOBI header length
    put(8, 2)                    # MOBI book type
    put(12, 65001)               # UTF-8
    put(16, uid)
    put(20, 2)                   # MOBI version
    put(24, 0xFFFFFFFF)          # orthographic index
    put(28, 0)                    # orthographic count
    put(32, 0xFFFFFFFF)          # extra index
    put(36, 0)                    # extra count
    put(40, 0xFFFFFFFF)          # first non-book index
    put(44, title_offset)
    put(48, title_length)
    put(52, 0x00000409)           # English locale
    put(56, 0)                    # input language
    put(60, 0)                    # output language
    put(64, 6)                    # minimum version
    put(68, first_image_record)
    put(72, 0xFFFFFFFF)           # Huff/CDIC record
    put(76, 0)
    put(80, 0)
    put(84, 0)
    put(88, 0)                    # EXTH flags
    put(92, 0)
    put(96, 0xFFFFFFFF)           # DRM offset
    put(100, 0)                   # DRM count
    put(104, 0)                   # DRM size
    put(108, 0)                   # DRM flags
    put(112, 1)                   # first content record
    put(116, text_record_count)   # last content record
    put(120, 0xFFFFFFFF)          # FCIS record
    put(124, 0)
    put(128, 0)
    put(132, 0xFFFFFFFF)          # FTSC record
    put(136, 0)
    put(140, 0)
    put(144, 0x00000409)          # source language
    put(148, 0)                   # language index
    put(152, 6)                   # MOBI version

    return bytes(header)


def _record_entry(offset: int, record_number: int) -> bytes:
    return _u32(offset) + bytes((0,)) + record_number.to_bytes(3, "big")


def _align4(data: bytearray) -> None:
    while len(data) % 4:
        data.append(0)


def pngs_to_mobi(
    image_paths: Iterable[Path],
    output_path: Path,
    *,
    title: str = "Manga",
) -> None:
    # paths = [Path(path) for path in image_paths]

    if not image_paths:
        raise ValueError("image_paths must not be empty")

    for path in image_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        # if path.suffix.lower() != ".png":
        #     raise ValueError(f"Only PNG files are supported: {path}")

    image_data = [path.read_bytes() for path in image_paths]

    uid = int.from_bytes(
        hashlib.sha1(b"".join(image_data)).digest()[:4],
        "big",
    )

    text_record_count = 1
    first_image_record = 1 + text_record_count

    html_parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:mbp="http://www.mobipocket.com/ns/mbp">',
        "<head><meta charset=\"utf-8\" /></head>",
        '<body>',
    ]

    for index in range(len(image_paths)):
        html_parts.append(
            f'<img recindex="{index + 1:05d}" width="600" height="600" />'
        )
        if index != len(image_paths) - 1:
            html_parts.append("<mbp:pagebreak />")

    html_parts.extend(("</body>", "</html>"))
    html = "\n".join(html_parts).encode("utf-8")

    text_records = [
        html[offset : offset + 4096]
        for offset in range(0, len(html), 4096)
    ]

    text_record_count = len(text_records)
    first_image_record = 1 + text_record_count

    html_parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:mbp="http://www.mobipocket.com/ns/mbp">',
        "<head><meta charset=\"utf-8\" /></head>",
        '<body>',
    ]

    for index in range(len(image_paths)):
        html_parts.append(
            f'<img recindex="{index + 1:05d}" width="600" height="600" />'
        )
        if index != len(image_paths) - 1:
            html_parts.append("<mbp:pagebreak />")

    html_parts.extend(("</body>", "</html>"))
    html = "\n".join(html_parts).encode("utf-8")

    text_records = [
        html[offset : offset + 4096]
        for offset in range(0, len(html), 4096)
    ]
    text_record_count = len(text_records)

    title_bytes = title.encode("utf-8")
    title_offset = 16 + 232

    record_zero = (
        _palm_doc_header(len(html), text_record_count)
        + _mobi_header(
            uid=uid,
            title_offset=title_offset,
            title_length=len(title_bytes),
            first_image_record=1 + text_record_count,
            text_record_count=text_record_count,
        )
        + title_bytes
        + b"\0"
    )

    records = [record_zero, *text_records, *image_data]
    record_count = len(records)
    directory_size = record_count * 8

    payload = bytearray()
    offsets = []
    current_offset = 78 + directory_size

    for record in records:
        aligned_offset = (current_offset + 3) & ~3
        payload.extend(b"\0" * (aligned_offset - current_offset))
        offsets.append(aligned_offset)
        payload.extend(record)
        current_offset = aligned_offset + len(record)

    directory = bytearray()
    for index, offset in enumerate(offsets):
        directory.extend(_record_entry(offset, index))

    final_data = bytearray()
    final_data.extend(_pdb_header("Manga", record_count, uid))
    final_data.extend(directory)
    final_data.extend(payload)

    Path(output_path).write_bytes(final_data)
