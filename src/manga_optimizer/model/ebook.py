from dataclasses import dataclass, field
import hashlib
import base64


@dataclass(frozen=True)
class Page:
    uri: str
    index: int
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
    uid: str
    title: str
    cover: Page
    pages: list[Page]
    orientation: Orientation = field(
        default=Orientation.PORTRAIT, kw_only=True)
    writing_mode: WritingMode = field(
        default=WritingMode.HORIZONTAL_RL, kw_only=True)

    def __init__(self, title: str, cover: Page, pages: list[Page]):
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "cover", cover)
        object.__setattr__(self, "pages", pages)
        object.__setattr__(self, "uid", Ebook._make_id(title+f"{len(pages)}"))

    @staticmethod
    def _make_id(seed: str) -> str:
        digest = hashlib.sha256(
            seed.strip().lower().encode("utf-8")
        ).digest()

        encoded = base64.b32encode(digest).decode("ascii")
        return 'B1' + str(encoded[:8])


@dataclass(frozen=True)
class Mobi(Ebook):
    asin: str
    doctype: MobiDocType
    original_size: tuple[int, int]

    def __init__(self, doctype: MobiDocType, original_size: tuple[int, int]):
        self.asin = self.uid
        self.doctype = doctype
        self.original_size = original_size
