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
            resolution[0] * ratio,
            resolution[1] * ratio
        )
        object.__setattr__(self, "color_resolution", color_resolution)

    # def __init__(self, alias: str, dpi: int, resolution: tuple[int, int], *, model: str | None = None, color_dpi: int | None = None, ) -> None:
    #     self.alias = alias
    #     self.model = model
    #     self.dpi = dpi
    #     self.resolution = resolution
    #     if color_dpi != None:
    #         self.color_dpi = color_dpi
    #         ratio = self.color_dpi/self.dpi
    #         self.color_resolution = (
    #             resolution[0] * ratio,
    #             resolution[1] * ratio
    #         )

    def has_color(self):
        return self.color_dpi is not None
