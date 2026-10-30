"""Pixel-art rendering helpers used by gameplay modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import pygame

"""
Colors:
0, -1 transparent
1 black
2 white
3 Red
4 Yellow
5 Blue
6 Brown
7 Green
8 Orange
9 Purple
"""

DEFAULT_PALETTE: dict[int, tuple[int, int, int, int]] = {
    -1: (0, 0, 0, 0),
    0: (0, 0, 0, 0),
    1: (0, 0, 0, 255),
    2: (255, 255, 255, 255),
    3: (255, 20, 20, 255),
    4: (248, 255, 0, 255),
    5: (0, 225, 225, 255),
    6: (131, 100, 0, 255),
    7: (0, 163, 0, 255),
    8: (255, 149, 21, 255),
    9: (155, 0, 178, 255),
    10: (0, 0, 0, 255),
    11: (0, 0, 0, 255),
    12: (0, 0, 0, 255),
    13: (0, 0, 0, 255),
    14: (0, 0, 0, 255),
    15: (0, 0, 0, 255),
    16: (0, 0, 0, 255),
    17: (0, 0, 0, 255),
    18: (0, 0, 0, 255),
}


@dataclass(frozen=True)
class CanvasConfig:
    """Shared layout constants.

    Default board is 16x16 cells at 32 px each, with a 2-cell border for a visible frame.
    """

    board_cells: int = 16
    cell_size: int = 32
    border_cells: int = 2

    @property
    def board_pixels(self) -> int:
        return self.board_cells * self.cell_size

    @property
    def canvas_size(self) -> tuple[int, int]:
        px = (self.board_cells + (self.border_cells * 2)) * self.cell_size
        return px, px

    @property
    def board_origin(self) -> tuple[int, int]:
        border_px = self.border_cells * self.cell_size
        return border_px, border_px

    @property
    def sprite_size(self) -> int:
        return max(1, int(round(self.cell_size * 0.8)))


class PixelArt:
    """Converts numeric grids into crisp pixel-art pygame surfaces."""

    def __init__(
        self,
        canvas: CanvasConfig | None = None,
        palette: Mapping[int, tuple[int, int, int, int]] | None = None,
    ) -> None:
        self._canvas = canvas or CanvasConfig()
        self._palette = dict(DEFAULT_PALETTE)
        if palette:
            self._palette.update(dict(palette))

    @property
    def canvas(self) -> CanvasConfig:
        return self._canvas

    @property
    def palette(self) -> dict[int, tuple[int, int, int, int]]:
        return dict(self._palette)

    def validate_grid(
        self,
        grid: Sequence[Sequence[int]],
        palette: Mapping[int, tuple[int, int, int, int]] | None = None,
    ) -> tuple[int, int]:
        if not grid:
            raise ValueError("Pixel grid cannot be empty")
        width = len(grid[0])
        if width == 0:
            raise ValueError("Pixel grid rows cannot be empty")

        active_palette = self._palette if palette is None else palette
        for y, row in enumerate(grid):
            if len(row) != width:
                raise ValueError(f"Pixel grid is not rectangular at row {y}")
            for x, value in enumerate(row):
                if not isinstance(value, int):
                    raise TypeError(f"Pixel value at ({x}, {y}) must be int")
                if value not in active_palette:
                    raise ValueError(f"Unknown palette index {value} at ({x}, {y})")

        return width, len(grid)

    def render(
        self,
        grid: Sequence[Sequence[int]],
        *,
        target_size: tuple[int, int] | None = None,
        palette: Mapping[int, tuple[int, int, int, int]] | None = None,
    ) -> pygame.Surface:
        active_palette = dict(self._palette)
        if palette:
            active_palette.update(dict(palette))
        width, height = self.validate_grid(grid, active_palette)

        source = pygame.Surface((width, height), pygame.SRCALPHA)
        for y, row in enumerate(grid):
            for x, value in enumerate(row):
                source.set_at((x, y), active_palette[value])

        if target_size is None:
            return source
        if target_size[0] <= 0 or target_size[1] <= 0:
            raise ValueError("target_size values must be positive")
        return pygame.transform.scale(source, target_size)

    def render_sprite(self, grid: Sequence[Sequence[int]]) -> pygame.Surface:
        return self.render(grid, target_size=(self._canvas.sprite_size, self._canvas.sprite_size))

    def render_canvas(self, grid: Sequence[Sequence[int]]) -> pygame.Surface:
        return self.render(grid, target_size=self._canvas.canvas_size)
