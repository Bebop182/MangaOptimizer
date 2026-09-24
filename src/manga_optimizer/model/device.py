from dataclasses import dataclass, field


@dataclass(frozen=True)
class Device:
    alias: str
    model: str | None
    dpi: int
    resolution: tuple[int, int]
    color_dpi: int | None = field(default=None)
    color_resolution: tuple[int, int] | None = field(default=None)

    def __post_init__(self):
        if not self.color_dpi:
            return

        ratio = self.color_dpi/self.dpi
        color_resolution = (
            self.resolution[0] * ratio,
            self.resolution[1] * ratio
        )
        object.__setattr__(self, "color_resolution", color_resolution)

    def has_color(self):
        return self.color_dpi is not None
