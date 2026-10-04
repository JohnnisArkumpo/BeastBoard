"""Board state and translucent rendering."""

from __future__ import annotations

from typing import Iterable

import pygame

try:
    from .pixel_art import CanvasConfig
except ImportError:  # pragma: no cover - script import fallback
    from pixel_art import CanvasConfig


class Board:
    """Simple 16x16 board with occupancy and collision helpers."""

    def __init__(self, canvas: CanvasConfig | None = None) -> None:
        self._canvas = canvas or CanvasConfig()
        self._width = 16
        self._height = 16
        self._occupied: set[tuple[int, int]] = set()

        self._grid_surface = pygame.Surface((self.pixel_width, self.pixel_height), pygame.SRCALPHA)
        self._build_grid_surface()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def cell_size(self) -> int:
        return self._canvas.cell_size

    @property
    def pixel_width(self) -> int:
        return self._width * self.cell_size

    @property
    def pixel_height(self) -> int:
        return self._height * self.cell_size

    @property
    def origin(self) -> tuple[int, int]:
        return self._canvas.board_origin

    @property
    def canvas_size(self) -> tuple[int, int]:
        return self._canvas.canvas_size

    def _build_grid_surface(self) -> None:
        color_a = (210, 210, 210, 95)
        color_b = (240, 240, 240, 110)
        for y in range(self._height):
            for x in range(self._width):
                rect = pygame.Rect(x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size)
                self._grid_surface.fill(color_a if (x + y) % 2 else color_b, rect)
        line_color = (70, 70, 70, 110)
        for x in range(self._width + 1):
            px = x * self.cell_size
            pygame.draw.line(self._grid_surface, line_color, (px, 0), (px, self.pixel_height), 1)
        for y in range(self._height + 1):
            py = y * self.cell_size
            pygame.draw.line(self._grid_surface, line_color, (0, py), (self.pixel_width, py), 1)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._width and 0 <= y < self._height

    def is_occupied(self, x: int, y: int) -> bool:
        return (x, y) in self._occupied

    def is_blocked(self, x: int, y: int) -> bool:
        return not self.in_bounds(x, y) or self.is_occupied(x, y)

    def can_move_to(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and not self.is_occupied(x, y)

    def set_occupied(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            raise ValueError(f"Cannot occupy out-of-bounds cell ({x}, {y})")
        self._occupied.add((x, y))

    def clear_occupied(self, x: int, y: int) -> None:
        self._occupied.discard((x, y))

    def replace_occupied(self, old_pos: tuple[int, int], new_pos: tuple[int, int]) -> bool:
        old_x, old_y = old_pos
        new_x, new_y = new_pos
        if not self.in_bounds(new_x, new_y) or self.is_occupied(new_x, new_y):
            return False
        self.clear_occupied(old_x, old_y)
        self.set_occupied(new_x, new_y)
        return True

    def set_occupied_many(self, positions: Iterable[tuple[int, int]]) -> None:
        for x, y in positions:
            self.set_occupied(x, y)

    def to_pixel(self, x: int, y: int) -> tuple[int, int]:
        ox, oy = self.origin
        return ox + (x * self.cell_size), oy + (y * self.cell_size)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._grid_surface, self.origin)
