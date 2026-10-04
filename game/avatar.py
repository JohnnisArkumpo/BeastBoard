"""Character, Avatar, and Villain gameplay entities."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

import pygame

try:
    from .pixel_art import PixelArt
except ImportError:  # pragma: no cover - script import fallback
    from pixel_art import PixelArt

if TYPE_CHECKING:
    try:
        from .board import Board
    except ImportError:  # pragma: no cover - script import fallback
        from board import Board


ATTACK_CHOICES = ("Y", "U", "I", "O", "P")
_MOVE_KEYS = {
    pygame.K_w: (0, -1, "up"),
    pygame.K_s: (0, 1, "down"),
    pygame.K_a: (-1, 0, "left"),
    pygame.K_d: (1, 0, "right"),
}
_ATTACK_KEYS = {
    pygame.K_y: "Y",
    pygame.K_u: "U",
    pygame.K_i: "I",
    pygame.K_o: "O",
    pygame.K_p: "P",
}


def _empty_sprite(fill: int = 0) -> list[list[int]]:
    return [[fill for _ in range(16)] for _ in range(16)]


def _invert_sprite(grid: list[list[int]]) -> list[list[int]]:
    return [[2 if value == 1 else 1 if value == 2 else value for value in row] for row in grid]


def _base_sprite(direction: str) -> list[list[int]]:
    sprite = _empty_sprite()

    for y in range(1, 5):
        for x in range(5, 11):
            sprite[y][x] = 2
    sprite[2][6] = 1
    sprite[2][9] = 1

    for y in range(5, 11):
        for x in range(6, 10):
            sprite[y][x] = 2
    sprite[7][7] = 1
    sprite[7][8] = 1

    for y in range(11, 15):
        sprite[y][6] = 2
        sprite[y][9] = 2

    if direction == "left":
        for x in range(2, 7):
            sprite[7][x] = 2
        sprite[6][3] = 2
    elif direction == "right":
        for x in range(9, 14):
            sprite[7][x] = 2
        sprite[6][12] = 2
    elif direction == "up":
        for y in range(4, 8):
            sprite[y][4] = 2
            sprite[y][11] = 2
    else:  # down
        for y in range(6, 10):
            sprite[y][4] = 2
            sprite[y][11] = 2

    return sprite


def _attack_sprite(direction: str) -> list[list[int]]:
    sprite = _base_sprite(direction)
    if direction == "left":
        for x in range(0, 5):
            sprite[7][x] = 1
    elif direction == "right":
        for x in range(11, 16):
            sprite[7][x] = 1
    elif direction == "up":
        for y in range(0, 4):
            sprite[y][7] = 1
        sprite[0][6] = 1
        sprite[0][8] = 1
    else:
        for y in range(12, 16):
            sprite[y][8] = 1
        sprite[15][7] = 1
        sprite[15][9] = 1
    return sprite


def _defend_sprite(direction: str) -> list[list[int]]:
    sprite = _base_sprite(direction)
    if direction in ("left", "right"):
        center = 3 if direction == "left" else 12
        for y in range(5, 11):
            for x in range(max(0, center - 1), min(16, center + 1)):
                sprite[y][x] = 1
    else:
        row = 4 if direction == "up" else 11
        for x in range(4, 12):
            sprite[row][x] = 1
    return sprite


def _death_sprite() -> list[list[int]]:
    sprite = _empty_sprite()
    for x in range(2, 14):
        sprite[10][x] = 1
    sprite[9][3] = 1
    sprite[9][12] = 1
    sprite[11][5] = 1
    sprite[11][10] = 1
    return sprite


def _level_up_sprite() -> list[list[int]]:
    sprite = _base_sprite("up")
    for point in ((1, 1), (14, 1), (1, 14), (14, 14), (7, 0), (0, 7), (15, 7), (7, 15)):
        x, y = point
        sprite[y][x] = 1
    return sprite


def _sprite_map(invert: bool = False) -> dict[str, list[list[int]]]:
    sprites = {
        "up": _base_sprite("up"),
        "down": _base_sprite("down"),
        "left": _base_sprite("left"),
        "right": _base_sprite("right"),
        "attack": _attack_sprite("right"),
        "defend": _defend_sprite("down"),
        "death": _death_sprite(),
        "level_up": _level_up_sprite(),
    }
    if invert:
        return {key: _invert_sprite(value) for key, value in sprites.items()}
    return sprites


class Character:
    """Base class for shared character behavior."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        *,
        pixel_art: PixelArt | None = None,
        invert_colors: bool = False,
        health: int = 3,
    ) -> None:
        self._name = name
        self._x = x
        self._y = y
        self._max_health = max(1, health)
        self._health = self._max_health
        self._level = 1
        self._state = "down"
        self._pixel_art = pixel_art or PixelArt()
        self._sprites = _sprite_map(invert=invert_colors)
        self._sprite_cache: dict[str, pygame.Surface] = {}

        self._turn_action_used = False
        self._alive = True
        self._visible = True
        self._dying_until = 0.0

    @property
    def name(self) -> str:
        return self._name

    @property
    def position(self) -> tuple[int, int]:
        return self._x, self._y

    @property
    def health(self) -> int:
        return self._health

    @property
    def level(self) -> int:
        return self._level

    @property
    def state(self) -> str:
        return self._state

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def visible(self) -> bool:
        return self._visible

    @property
    def can_act(self) -> bool:
        return self._alive and self._visible and not self._turn_action_used

    def place_on_board(self, board: Board) -> None:
        board.set_occupied(self._x, self._y)

    def start_turn(self) -> None:
        self._turn_action_used = False

    def end_turn(self) -> None:
        self._turn_action_used = True

    def _consume_turn_action(self) -> None:
        self._turn_action_used = True

    @classmethod
    def resolve_combat(cls, attacker_choice: str, defender_choice: str) -> int:
        """Return 1 attacker win, -1 attacker loss, 0 tie."""

        attacker = attacker_choice.upper()
        defender = defender_choice.upper()
        if attacker not in ATTACK_CHOICES or defender not in ATTACK_CHOICES:
            raise ValueError("Combat choices must be one of Y/U/I/O/P")

        if attacker == defender:
            return 0

        attacker_idx = ATTACK_CHOICES.index(attacker)
        defender_idx = ATTACK_CHOICES.index(defender)
        distance = (defender_idx - attacker_idx) % len(ATTACK_CHOICES)
        return 1 if distance in (1, 2) else -1

    def move_to(self, x: int, y: int, board: Board, *, facing: str | None = None) -> bool:
        if not self.can_act:
            return False
        if board.replace_occupied((self._x, self._y), (x, y)):
            self._x, self._y = x, y
            if facing:
                self._state = facing
            self._consume_turn_action()
            return True
        return False

    def defend(self) -> bool:
        if not self.can_act:
            return False
        self._state = "defend"
        self._consume_turn_action()
        return True

    def level_up(self) -> None:
        self._level += 1
        self._health = min(self._max_health + self._level, self._health + 1)
        self._state = "level_up"

    def take_damage(self, amount: int = 1, *, now: float | None = None, death_duration: float = 0.35) -> None:
        if not self._alive:
            return
        self._health -= max(0, amount)
        if self._health <= 0:
            self.die(now=now, death_duration=death_duration)

    def die(self, *, now: float | None = None, death_duration: float = 0.35) -> None:
        if not self._alive:
            return
        current = time.monotonic() if now is None else now
        self._alive = False
        self._state = "death"
        self._dying_until = current + max(0.1, death_duration)
        self._consume_turn_action()

    def update(self, board: Board, *, now: float | None = None) -> None:
        if self._alive or not self._visible:
            return
        current = time.monotonic() if now is None else now
        if current >= self._dying_until:
            self._visible = False
            board.clear_occupied(self._x, self._y)

    def _get_sprite(self) -> pygame.Surface:
        sprite_key = self._state if self._state in self._sprites else "down"
        if sprite_key not in self._sprite_cache:
            self._sprite_cache[sprite_key] = self._pixel_art.render_sprite(self._sprites[sprite_key])
        return self._sprite_cache[sprite_key]

    def draw(self, surface: pygame.Surface, board: Board) -> None:
        if not self._visible:
            return
        sprite = self._get_sprite()
        cell_x, cell_y = board.to_pixel(self._x, self._y)
        inset = (board.cell_size - sprite.get_width()) // 2
        surface.blit(sprite, (cell_x + inset, cell_y + inset))


class Avatar(Character):
    """Player-controlled character."""

    def __init__(self, name: str, x: int, y: int, *, pixel_art: PixelArt | None = None) -> None:
        super().__init__(name, x, y, pixel_art=pixel_art, invert_colors=False, health=5)
        self._queued_attack_choice = "Y"

    @property
    def queued_attack_choice(self) -> str:
        return self._queued_attack_choice

    def set_attack_choice(self, choice: str) -> None:
        value = choice.upper()
        if value not in ATTACK_CHOICES:
            raise ValueError("Attack choice must be one of Y/U/I/O/P")
        self._queued_attack_choice = value

    def _adjacent_villain(self, villains: list["Villain"]) -> "Villain | None":
        for villain in villains:
            if not villain.visible:
                continue
            vx, vy = villain.position
            if abs(vx - self._x) + abs(vy - self._y) == 1:
                return villain
        return None

    def _resolve_attack(self, villain: "Villain", choice: str, *, now: float | None = None) -> dict[str, str]:
        self._state = "attack"
        villain_choice = villain.choose_combat_choice()
        outcome = self.resolve_combat(choice, villain_choice)
        if outcome > 0:
            villain.take_damage(now=now)
            result = "win"
        elif outcome < 0:
            self.take_damage(now=now)
            result = "lose"
        else:
            result = "tie"
        self._consume_turn_action()
        return {"action": "attack", "attacker": choice, "defender": villain_choice, "result": result}

    def try_move(self, dx: int, dy: int, board: Board, villains: list["Villain"], *, facing: str, now: float | None = None) -> dict[str, str]:
        if not self.can_act:
            return {"action": "move", "result": "blocked_turn"}

        target = (self._x + dx, self._y + dy)
        for villain in villains:
            if villain.visible and villain.position == target:
                return self._resolve_attack(villain, self._queued_attack_choice, now=now)

        moved = self.move_to(target[0], target[1], board, facing=facing)
        if moved:
            return {"action": "move", "result": "moved"}

        return {"action": "move", "result": "blocked"}

    def attack_adjacent(self, board: Board, villains: list["Villain"], choice: str, *, now: float | None = None) -> dict[str, str]:
        _ = board  # reserved for future targeted attacks
        if not self.can_act:
            return {"action": "attack", "result": "blocked_turn"}
        self.set_attack_choice(choice)
        target = self._adjacent_villain(villains)
        if target is None:
            self._state = "attack"
            self._consume_turn_action()
            return {"action": "attack", "result": "no_target", "attacker": self._queued_attack_choice}
        return self._resolve_attack(target, self._queued_attack_choice, now=now)

    def handle_input(self, key: int, board: Board, villains: list["Villain"], *, now: float | None = None) -> dict[str, str] | None:
        if key in _MOVE_KEYS:
            dx, dy, facing = _MOVE_KEYS[key]
            return self.try_move(dx, dy, board, villains, facing=facing, now=now)
        if key in _ATTACK_KEYS:
            return self.attack_adjacent(board, villains, _ATTACK_KEYS[key], now=now)
        return None


class Villain(Character):
    """Enemy character with random combat choices."""

    def __init__(self, name: str, x: int, y: int, *, pixel_art: PixelArt | None = None, rng: random.Random | None = None) -> None:
        super().__init__(name, x, y, pixel_art=pixel_art, invert_colors=True, health=3)
        self._rng = rng or random.Random()

    def choose_combat_choice(self) -> str:
        return self._rng.choice(ATTACK_CHOICES)
