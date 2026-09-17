from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import base64


@dataclass(frozen=True)
class Page:
    uri: str
    number: int
    title: str | None


class Orientation:
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    AUTO = "auto"


class WritingMode:
    HORIZONTAL_LR = "horizontal_lr"
    HORIZONTAL_RL = "horizontal_rl"


class MobiDocType:
    PDOC: "PDOC"
    EBOK: "EBOK"


@dataclass(frozen=True)
class Ebook:
    uid: str = field(init=False)
    title: str
    cover: Page
    pages: list[Page]
    orientation: Orientation = field(
        default=Orientation.PORTRAIT, kw_only=True)
    writing_mode: WritingMode = field(
        default=WritingMode.HORIZONTAL_RL, kw_only=True)
    language: str = "en"

    def __post_init__(self):
        object.__setattr__(self, "uid", Ebook._make_id(
            self.title+f"{len(self.pages)}"))

    @classmethod
    def from_book(
        cls,
        book: Ebook,
        *,
        title: str | None = None,
        cover: Page | None = None,
        pages: list[Page] | None = None,
    ) -> Ebook:
        return replace(
            book,
            title=title if title is not None else book.title,
            cover=cover if cover is not None else book.cover,
            pages=pages if pages is not None else book.pages,
        )

    @staticmethod
    def _make_id(seed: str) -> str:
        digest = hashlib.sha256(
            seed.strip().lower().encode("utf-8")
        ).digest()

        encoded = base64.b32encode(digest).decode("ascii")
        return "B1" + str(encoded[:8])
