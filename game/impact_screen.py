"""Timed full-canvas impact overlays."""

from __future__ import annotations

import time

import pygame

try:
    from .pixel_art import PixelArt
except ImportError:  # pragma: no cover - script import fallback
    from pixel_art import PixelArt


class ImpactScreen:
    """Displays short pixel-art overlays in front of gameplay."""

    _ALLOWED_DURATIONS = (0.5, 1.0)

    def __init__(self, pixel_art: PixelArt | None = None) -> None:
        self._pixel_art = pixel_art or PixelArt()
        self._art: dict[str, list[list[int]]] = {
            "hit": self._radial_art(5, 0),
            "block": self._stripe_art(6, 0),
            "level_up": self._radial_art(7, 8),
            "defeat": self._stripe_art(5, 9),
        }
        self._cache: dict[str, pygame.Surface] = {}
        self._active_name: str | None = None
        self._active_until: float = 0.0

    @staticmethod
    def _radial_art(primary: int, secondary: int, size: int = 40) -> list[list[int]]:
        center = size // 2
        art: list[list[int]] = []
        for y in range(size):
            row: list[int] = []
            for x in range(size):
                dist = abs(x - center) + abs(y - center)
                if dist < size // 5:
                    row.append(primary)
                elif dist < size // 3:
                    row.append(secondary)
                elif dist % 3 == 0:
                    row.append(primary)
                else:
                    row.append(0)
            art.append(row)
        return art

    @staticmethod
    def _stripe_art(primary: int, secondary: int, size: int = 40) -> list[list[int]]:
        art: list[list[int]] = []
        for y in range(size):
            row: list[int] = []
            for x in range(size):
                if (x + y) % 7 in (0, 1):
                    row.append(primary)
                elif (x - y) % 9 == 0:
                    row.append(secondary)
                else:
                    row.append(0)
            art.append(row)
        return art

    @property
    def is_active(self) -> bool:
        return self._active_name is not None and time.monotonic() < self._active_until

    def activate(self, name: str, duration: float = 0.5, now: float | None = None) -> None:
        key = name if name in self._art else "hit"
        self._active_name = key
        seconds = duration if duration in self._ALLOWED_DURATIONS else min(self._ALLOWED_DURATIONS, key=lambda v: abs(v - duration))
        current = time.monotonic() if now is None else now
        self._active_until = current + seconds

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
