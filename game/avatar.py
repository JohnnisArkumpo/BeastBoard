"""Character, Avatar, and Villain gameplay entities."""

from __future__ import annotations

from dataclasses import dataclass
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
MOVE_KEYS = {
    pygame.K_w: (0, -1, "up"),
    pygame.K_s: (0, 1, "down"),
    pygame.K_a: (-1, 0, "left"),
    pygame.K_d: (1, 0, "right"),
}
ATTACK_KEYS = {
    pygame.K_y: "Y",
    pygame.K_u: "U",
    pygame.K_i: "I",
    pygame.K_o: "O",
    pygame.K_p: "P",
}


def defeats_required_for_level(level: int) -> int:
    """Near-exponential defeats needed for each avatar level step."""

    return max(2, int(round((1.58 ** max(0, level - 1)) * 2.4)))


def resolve_rps_result(attacker_choice: str, defender_choice: str) -> int:
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


@dataclass(frozen=True)
class DuelResult:
    """Final score output for one score-based duel."""

    avatar_choice: str
    enemy_choice: str
    avatar_score: int
    enemy_score: int
    rps_result: int
    winner: str
    impervious_blocked: bool = False


def resolve_score_duel(
    *,
    avatar_choice: str,
    enemy_choice: str,
    avatar_base_attack: int,
    enemy_base_attack: int,
    avatar_win_modifier: int,
    avatar_loss_modifier: int,
    enemy_win_modifier: int,
    enemy_loss_modifier: int,
    enemy_impervious_choice: str | None = None,
) -> DuelResult:
    """Resolve one combat round using score totals and per-attack modifiers."""

    avatar_pick = avatar_choice.upper()
    enemy_pick = enemy_choice.upper()
    rps_result = resolve_rps_result(avatar_pick, enemy_pick)

    avatar_score = avatar_base_attack
    enemy_score = enemy_base_attack
    impervious_blocked = False

    enemy_impervious = enemy_impervious_choice is not None and enemy_pick == enemy_impervious_choice.upper()

    if rps_result > 0:
        if not enemy_impervious:
            avatar_score += avatar_win_modifier
        else:
            impervious_blocked = True
        enemy_score += enemy_loss_modifier
    elif rps_result < 0:
        avatar_score += avatar_loss_modifier
        enemy_score += enemy_win_modifier

    if enemy_impervious and rps_result > 0 and avatar_score >= enemy_score:
        enemy_score = avatar_score

    if avatar_score > enemy_score:
        winner = "avatar"
    elif avatar_score < enemy_score:
        winner = "enemy"
    else:
        winner = "tie"

    return DuelResult(
        avatar_choice=avatar_pick,
        enemy_choice=enemy_pick,
        avatar_score=avatar_score,
        enemy_score=enemy_score,
        rps_result=rps_result,
        winner=winner,
        impervious_blocked=impervious_blocked,
    )


def _empty_sprite(fill: int = 0) -> list[list[int]]:
    return [[fill for _ in range(16)] for _ in range(16)]


def _humanoid_sprite(primary: int, secondary: int, accent: int, facing: str) -> list[list[int]]:
    sprite = _empty_sprite()

    for y in range(1, 5):
        for x in range(5, 11):
            sprite[y][x] = primary
    sprite[2][6] = secondary
    sprite[2][9] = secondary

    for y in range(5, 11):
        for x in range(6, 10):
            sprite[y][x] = primary

    sprite[5][7] = accent
    sprite[5][8] = accent
    sprite[8][7] = secondary
    sprite[8][8] = secondary

    for y in range(11, 15):
        sprite[y][6] = primary
        sprite[y][9] = primary

    if facing == "left":
        for x in range(2, 7):
            sprite[7][x] = primary
        sprite[6][3] = accent
    elif facing == "right":
        for x in range(9, 14):
            sprite[7][x] = primary
        sprite[6][12] = accent
    elif facing == "up":
        for y in range(4, 8):
            sprite[y][4] = primary
            sprite[y][11] = primary
    else:
        for y in range(6, 10):
            sprite[y][4] = primary
            sprite[y][11] = primary

    return sprite


def _attack_sprite(base: list[list[int]], facing: str, slash_color: int) -> list[list[int]]:
    sprite = [row[:] for row in base]
    if facing == "left":
        for x in range(0, 4):
            sprite[7][x] = slash_color
    elif facing == "right":
        for x in range(12, 16):
            sprite[7][x] = slash_color
    elif facing == "up":
        for y in range(0, 4):
            sprite[y][7] = slash_color
            sprite[y][8] = slash_color
    else:
        for y in range(12, 16):
            sprite[y][7] = slash_color
            sprite[y][8] = slash_color
    return sprite


def _death_sprite(body: int, blood: int) -> list[list[int]]:
    sprite = _empty_sprite()
    for x in range(2, 14):
        sprite[10][x] = body
    for x in range(4, 12):
        sprite[9][x] = blood if x % 2 else body
    sprite[8][5] = body
    sprite[8][10] = body
    sprite[11][6] = body
    sprite[11][9] = body
    return sprite


def _level_up_sprite(base: list[list[int]], glow: int) -> list[list[int]]:
    sprite = [row[:] for row in base]
    for x, y in ((1, 1), (14, 1), (1, 14), (14, 14), (7, 0), (0, 7), (15, 7), (7, 15), (8, 15)):
        sprite[y][x] = glow
    return sprite


def _boss_sprite() -> dict[str, list[list[int]]]:
    def body(facing: str) -> list[list[int]]:
        sprite = _empty_sprite()
        for y in range(2, 13):
            for x in range(3, 13):
                sprite[y][x] = 5 if (x + y) % 2 else 9

        for x in (5, 10):
            sprite[1][x] = 7
            sprite[0][x] = 7

        sprite[4][6] = 2
        sprite[4][9] = 2
        for x in range(6, 10):
            sprite[8][x] = 4

        for y in range(13, 16):
            sprite[y][5] = 9
            sprite[y][10] = 9

        if facing == "left":
            for y in range(7, 12):
                sprite[y][2] = 7
        elif facing == "right":
            for y in range(7, 12):
                sprite[y][13] = 7
        elif facing == "up":
            for x in range(6, 10):
                sprite[1][x] = 7
        else:
            for x in range(6, 10):
                sprite[14][x] = 7

        return sprite

    right = body("right")
    return {
        "up": body("up"),
        "down": body("down"),
        "left": body("left"),
        "right": right,
        "attack": _attack_sprite(right, "right", 7),
        "death": _death_sprite(9, 5),
        "level_up": _level_up_sprite(right, 7),
    }


def _sprite_map(primary: int, secondary: int, accent: int, slash: int) -> dict[str, list[list[int]]]:
    down = _humanoid_sprite(primary, secondary, accent, "down")
    return {
        "up": _humanoid_sprite(primary, secondary, accent, "up"),
        "down": down,
        "left": _humanoid_sprite(primary, secondary, accent, "left"),
        "right": _humanoid_sprite(primary, secondary, accent, "right"),
        "attack": _attack_sprite(_humanoid_sprite(primary, secondary, accent, "right"), "right", slash),
        "death": _death_sprite(primary, accent),
        "level_up": _level_up_sprite(down, slash),
    }


class Character:
    """Base class for shared character behavior."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        *,
        pixel_art: PixelArt | None = None,
        sprites: dict[str, list[list[int]]] | None = None,
    ) -> None:
        self._name = name
        self._x = x
        self._y = y
        self._pixel_art = pixel_art or PixelArt()
        self._sprites = sprites or _sprite_map(2, 1, 4, 7)
        self._sprite_cache: dict[str, pygame.Surface] = {}

        self._state = "down"
        self._alive = True
        self._visible = True
        self._death_until = 0.0

        self.base_attack = 5
        self.win_modifiers = {choice: 3 for choice in ATTACK_CHOICES}
        self.loss_modifiers = {choice: 0 for choice in ATTACK_CHOICES}

    @property
    def name(self) -> str:
        return self._name

    @property
    def position(self) -> tuple[int, int]:
        return self._x, self._y

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def visible(self) -> bool:
        return self._visible

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        if state in self._sprites:
            self._state = state

    def set_position(self, x: int, y: int) -> None:
        self._x, self._y = x, y

    def revive(self) -> None:
        self._alive = True
        self._visible = True
        self._state = "down"
        self._death_until = 0.0

    def place_on_board(self, board: Board) -> None:
        board.set_occupied(self._x, self._y)

    def choose_combat_choice(self) -> str:
        return "Y"

    def begin_death(self, *, now: float | None = None, duration: float = 0.45) -> None:
        if not self._alive:
            return
        self._alive = False
        self._state = "death"
        current = time.monotonic() if now is None else now
        self._death_until = current + max(0.1, duration)

    def update(self, board: Board, *, now: float | None = None) -> None:
        if self._alive or not self._visible:
            return
        current = time.monotonic() if now is None else now
        if current >= self._death_until:
            self._visible = False
            board.clear_occupied(self._x, self._y)

    def _sprite_surface(self) -> pygame.Surface:
        key = self._state if self._state in self._sprites else "down"
        if key not in self._sprite_cache:
            self._sprite_cache[key] = self._pixel_art.render_sprite(self._sprites[key])
        return self._sprite_cache[key]

    def draw(self, surface: pygame.Surface, board: Board) -> None:
        if not self._visible:
            return
        sprite = self._sprite_surface()
        cell_x, cell_y = board.to_pixel(self._x, self._y)
        inset = (board.cell_size - sprite.get_width()) // 2
        surface.blit(sprite, (cell_x + inset, cell_y + inset))


class Avatar(Character):
    """Player-controlled character and progression stats."""

    def __init__(self, name: str, x: int, y: int, *, pixel_art: PixelArt | None = None) -> None:
        super().__init__(name, x, y, pixel_art=pixel_art, sprites=_sprite_map(2, 1, 4, 7))
        self._state = "down"
        self.level = 1
        self.total_defeats = 0
        self._next_level_total = defeats_required_for_level(1)
        self.pending_level_ups = 0
        self.redo_charges = 1
        self.current_target_id: int | None = None
        self.queued_attack_choice = "Y"

    @property
    def defeats_to_next_level(self) -> int:
        return max(0, self._next_level_total - self.total_defeats)

    def register_defeat(self, defeated_count: int = 1) -> int:
        self.total_defeats += max(0, defeated_count)
        gained = 0
        while self.total_defeats >= self._next_level_total:
            self.level += 1
            gained += 1
            self.pending_level_ups += 1
            self._next_level_total += defeats_required_for_level(self.level)
            self._state = "level_up"
        return gained

    def apply_level_up(self, option: int, attack_choice: str | None = None) -> bool:
        if self.pending_level_ups <= 0:
            return False
        if option == 1:
            self.base_attack += 1
        elif option == 2 and attack_choice in ATTACK_CHOICES:
            self.win_modifiers[attack_choice] += 2
        elif option == 3 and attack_choice in ATTACK_CHOICES:
            self.loss_modifiers[attack_choice] += 1
        elif option == 4:
            self.redo_charges += 1
        else:
            return False

        self.pending_level_ups -= 1
        self._state = "down"
        return True

    def choose_combat_choice(self) -> str:
        return self.queued_attack_choice

    def set_attack_choice(self, choice: str) -> None:
        upper = choice.upper()
        if upper not in ATTACK_CHOICES:
            raise ValueError("Attack choice must be one of Y/U/I/O/P")
        self.queued_attack_choice = upper

    def move(self, dx: int, dy: int, board: Board, *, facing: str) -> bool:
        target_x = self._x + dx
        target_y = self._y + dy
        if board.replace_occupied((self._x, self._y), (target_x, target_y)):
            self._x, self._y = target_x, target_y
            self._state = facing
            return True
        return False


class Villain(Character):
    """Enemy character with random combat choices."""

    _VARIANT_COLORS = (
        (5, 1, 7, 7),
        (6, 2, 7, 7),
        (8, 2, 9, 7),
        (9, 2, 5, 7),
    )

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        *,
        level: int,
        variant_index: int,
        pixel_art: PixelArt | None = None,
        rng: random.Random | None = None,
        is_boss: bool = False,
    ) -> None:
        sprites = _boss_sprite() if is_boss else _sprite_map(*self._VARIANT_COLORS[variant_index % len(self._VARIANT_COLORS)])
        super().__init__(name, x, y, pixel_art=pixel_art, sprites=sprites)
        self._rng = rng or random.Random()
        self.is_boss = is_boss
        self.lives = 3 if is_boss else 1

        self._apply_level_scaling(level, variant_index)

    def _apply_level_scaling(self, level: int, variant_index: int) -> None:
        if level <= 1:
            return

        self.base_attack += (level - 1) // 2
        boosted = (variant_index + level) % len(ATTACK_CHOICES)
        alt = (boosted + 2) % len(ATTACK_CHOICES)
        self.win_modifiers[ATTACK_CHOICES[boosted]] += level - 1
        self.win_modifiers[ATTACK_CHOICES[alt]] += max(1, level // 2)

        if (variant_index + level) % 2 == 0:
            self.base_attack += 1
        self.loss_modifiers[ATTACK_CHOICES[(boosted + 1) % len(ATTACK_CHOICES)]] += level // 2

    def choose_combat_choice(self) -> str:
        return self._rng.choice(ATTACK_CHOICES)

    def lose_life(self, *, now: float | None = None) -> bool:
        self.lives -= 1
        if self.lives <= 0:
            self.begin_death(now=now)
            return True
        self._state = "attack"
        return False


__all__ = [
    "ATTACK_CHOICES",
    "ATTACK_KEYS",
    "MOVE_KEYS",
    "Avatar",
    "Character",
    "DuelResult",
    "Villain",
    "defeats_required_for_level",
    "resolve_rps_result",
    "resolve_score_duel",
]
