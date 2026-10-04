"""Timed full-canvas impact overlays."""

from __future__ import annotations

import time

import pygame

try:
    from .pixel_art import PixelArt
except ImportError:  # pragma: no cover - script import fallback
    from pixel_art import PixelArt


class ImpactScreen:
    """Displays pixel-art overlays in front of gameplay."""

    SHORT_DURATION = 0.8
    LONG_DURATION = 1.6

    def __init__(self, pixel_art: PixelArt | None = None) -> None:
        self._pixel_art = pixel_art or PixelArt()
        self._art: dict[str, list[list[int]]] = {
            "level_up": self._level_up_art(),
            "door_ready": self._door_ready_art(),
            "door_enter": self._door_enter_art(),
            "final_kill": self._final_kill_art(),
            "avatar_death": self._avatar_death_art(),
            "boss_damage": self._boss_damage_art(),
        }
        self._cache: dict[str, pygame.Surface] = {}
        self._active_name: str | None = None
        self._active_until: float = 0.0

    @staticmethod
    def _blank(size: int = 40) -> list[list[int]]:
        return [[0 for _ in range(size)] for _ in range(size)]

    @staticmethod
    def _draw_box(art: list[list[int]], x0: int, y0: int, x1: int, y1: int, color: int, fill: int | None = None) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if x in (x0, x1) or y in (y0, y1):
                    art[y][x] = color
                elif fill is not None:
                    art[y][x] = fill

    @classmethod
    def _level_up_art(cls) -> list[list[int]]:
        art = cls._blank()
        cls._draw_box(art, 15, 12, 24, 28, 2, 1)
        art[14][18] = 7
        art[14][21] = 7
        for y in range(17, 23):
            art[y][13] = 8
            art[y][26] = 8
        for px in ((11, 11), (28, 11), (11, 28), (28, 28), (19, 9), (19, 31)):
            art[px[1]][px[0]] = 7
        return art

    @classmethod
    def _door_ready_art(cls) -> list[list[int]]:
        art = cls._blank()
        cls._draw_box(art, 14, 9, 25, 30, 7, 9)
        cls._draw_box(art, 16, 12, 23, 29, 2, 4)
        art[22][20] = 7
        for i in range(5):
            art[18][7 + i] = 8
            art[18][32 - i] = 8
        return art

    @classmethod
    def _door_enter_art(cls) -> list[list[int]]:
        art = cls._door_ready_art()
        cls._draw_box(art, 17, 17, 22, 28, 1, 2)
        art[18][19] = 4
        art[18][20] = 4
        for y in range(14, 18):
            art[y][15] = 8
            art[y][24] = 8
        return art

    @classmethod
    def _final_kill_art(cls) -> list[list[int]]:
        art = cls._blank()
        cls._draw_box(art, 6, 12, 14, 24, 2, 1)
        for x in range(16, 26):
            art[18][x] = 7
            art[19][x] = 7
        cls._draw_box(art, 27, 16, 34, 25, 5, 4)
        for x in range(27, 35):
            art[26][x] = 5
        return art

    @classmethod
    def _avatar_death_art(cls) -> list[list[int]]:
        art = cls._blank()
        cls._draw_box(art, 6, 10, 14, 24, 5, 9)
        for x in range(16, 26):
            art[17][x] = 5
            art[18][x] = 5
        cls._draw_box(art, 27, 17, 34, 25, 2, 1)
        for x in range(27, 35):
            art[26][x] = 2
        return art

    @classmethod
    def _boss_damage_art(cls) -> list[list[int]]:
        art = cls._blank()
        center = 20
        art[center][center] = 2
        for i in range(1, 8):
            art[center][center - i] = 7
            art[center][center + i] = 7
            art[center - i][center] = 7
            art[center + i][center] = 7
            if i < 6:
                art[center - i][center - i] = 5
                art[center + i][center + i] = 5
                art[center - i][center + i] = 5
                art[center + i][center - i] = 5
        return art

    @property
    def is_active(self) -> bool:
        return self._active_name is not None and time.monotonic() < self._active_until

    @property
    def active_name(self) -> str | None:
        return self._active_name

    def activate(self, name: str, *, long: bool = False, now: float | None = None) -> None:
        if name not in self._art:
            return
        self._active_name = name
        duration = self.LONG_DURATION if long else self.SHORT_DURATION
        current = time.monotonic() if now is None else now
        self._active_until = current + duration

    def update(self, now: float | None = None) -> None:
        if self._active_name is None:
            return
        current = time.monotonic() if now is None else now
        if current >= self._active_until:
            self._active_name = None

    def _get_surface(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = self._pixel_art.render_canvas(self._art[name])
        return self._cache[name]

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_active or self._active_name is None:
            return
        surface.blit(self._get_surface(self._active_name), (0, 0))
