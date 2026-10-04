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
            1: self._level_one(),
            2: self._level_two(),
            3: self._level_three(),
            4: self._level_four(),
            5: self._level_five(),
        }
        self._cache: dict[int, pygame.Surface] = {}
        self._level = 1

    @staticmethod
    def _size() -> int:
        return 40

    @classmethod
    def _frame(cls, inner_fn) -> list[list[int]]:
        size = cls._size()
        art: list[list[int]] = []
        for y in range(size):
            row: list[int] = []
            for x in range(size):
                if x in (0, 1, size - 2, size - 1) or y in (0, 1, size - 2, size - 1):
                    row.append(2)
                else:
                    row.append(inner_fn(x, y, size))
            art.append(row)
        return art

    @classmethod
    def _level_one(cls) -> list[list[int]]:
        def fill(x: int, y: int, size: int) -> int:
            horizon = int(size * 0.52)
            if y < horizon:
                return 6 if (x + y) % 7 else 2
            ridge = horizon + ((x // 3) % 3)
            if y < ridge:
                return 3
            return 8 if (x + y) % 5 else 7

        return cls._frame(fill)

    @classmethod
    def _level_two(cls) -> list[list[int]]:
        def fill(x: int, y: int, size: int) -> int:
            horizon = int(size * 0.46)
            if y < horizon:
                return 6 if (x + (y * 2)) % 6 else 2
            dune = horizon + ((x // 2) % 4)
            if y < dune:
                return 7
            return 9 if (x // 2 + y // 3) % 3 else 3

        return cls._frame(fill)

    @classmethod
    def _level_three(cls) -> list[list[int]]:
        def fill(x: int, y: int, size: int) -> int:
            horizon = int(size * 0.5)
            if y < horizon:
                return 6 if (x + y) % 6 else 2
            center = (size // 2, horizon + 4)
            ring = abs(x - center[0]) + abs(y - center[1])
            if ring < 6:
                return 7
            if y > horizon + ((x % 4) + 2):
                return 8
            return 4

        return cls._frame(fill)

    @classmethod
    def _level_four(cls) -> list[list[int]]:
        def fill(x: int, y: int, size: int) -> int:
            horizon = int(size * 0.42)
            if y < horizon:
                return 9 if (x + y) % 5 else 2
            if y < horizon + (x % 5):
                return 4
            return 7 if (x + (y * 3)) % 4 else 5

        return cls._frame(fill)

    @classmethod
    def _level_five(cls) -> list[list[int]]:
        def fill(x: int, y: int, size: int) -> int:
            horizon = int(size * 0.4)
            if y < horizon:
                return 9 if (x + y) % 5 else 2
            lava = (x * 3 + y * 2) % 9
            if lava in (0, 1, 2, 3):
                return 5
            if abs(x - y) % 7 == 0 or abs((size - 1 - x) - y) % 7 == 0 or y > horizon + 10:
                return 7
            return 4

        return cls._frame(fill)

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
