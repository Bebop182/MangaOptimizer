from dataclasses import dataclass, field


@dataclass(frozen=True)
class Device:
    alias: str
    model: str | None
    format: str
    dpi: int
    width: int
    height: int
    color_dpi: int | None = field(default=None)

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def color_resolution(self) -> tuple[int, int] | None:
        if self.color_dpi == None:
            return None
        ratio = int(self.color_dpi/self.dpi)
        return (self.width * ratio, self.height*ratio)

    def __post_init__(self):
        ...

    def has_color(self):
        return self.color_dpi is not None

    @classmethod
    def from_config(cls, short_name: str, values: dict) -> "Device":
        return cls(alias=short_name, **values)
