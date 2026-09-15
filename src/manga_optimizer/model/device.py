from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    alias: str
    model: str | None
    dpi: int
    resolution: tuple[int, int]
    color_dpi: int | None
    color_resolution: tuple[int, int] | None

    def __init__(self, alias: str, dpi: int, resolution: tuple[int, int], *, model: str | None, color_dpi: int | None, ) -> None:
        self.alias = alias
        self.model = model
        self.dpi = dpi
        self.resolution = resolution
        if color_dpi != None:
            self.color_dpi = color_dpi
            ratio = self.color_dpi/self.dpi
            self.color_resolution = (
                resolution[0] * ratio,
                resolution[1] * ratio
            )

    def has_color(self):
        return self.color_dpi is not None
