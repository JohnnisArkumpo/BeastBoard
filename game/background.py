"""Level-based still background rendering."""

from __future__ import annotations

import pygame

try:
    from .pixel_art import PixelArt
except ImportError:  # pragma: no cover - script import fallback
    from pixel_art import PixelArt


class Background:
    """Draws static level backgrounds behind the board."""

    def __init__(self, pixel_art: PixelArt | None = None) -> None:
        self._pixel_art = pixel_art or PixelArt()
        self._art_by_level: dict[int, list[list[int]]] = {
            1: self._make_checker(6, 3),
            2: self._make_stripes(8, 9),
            3: self._make_diagonal(5, 4),
        }
        self._cache: dict[int, pygame.Surface] = {}
        self._level = 1

    @staticmethod
    def _make_checker(primary: int, secondary: int, size: int = 32) -> list[list[int]]:
        return [[primary if (x + y) % 2 else secondary for x in range(size)] for y in range(size)]

    @staticmethod
    def _make_stripes(primary: int, secondary: int, size: int = 32) -> list[list[int]]:
        return [[primary if (x // 2) % 2 else secondary for x in range(size)] for _ in range(size)]

    @staticmethod
    def _make_diagonal(primary: int, secondary: int, size: int = 32) -> list[list[int]]:
        return [[primary if (x - y) % 5 in (0, 1) else secondary for x in range(size)] for y in range(size)]

    @property
    def level(self) -> int:
        return self._level

    def set_level(self, level: int) -> None:
        self._level = int(level)

    def _resolve_level(self, level: int) -> int:
        return level if level in self._art_by_level else 1

    def get_surface(self, level: int | None = None) -> pygame.Surface:
        resolved = self._resolve_level(self._level if level is None else int(level))
        if resolved not in self._cache:
            self._cache[resolved] = self._pixel_art.render_canvas(self._art_by_level[resolved])
        return self._cache[resolved]

    def draw(self, surface: pygame.Surface, level: int | None = None) -> None:
        surface.blit(self.get_surface(level), (0, 0))
