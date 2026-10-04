"""Playable BeastBoard game runtime."""

from __future__ import annotations

import os
import random
from typing import Iterable

import pygame

try:
    from .avatar import ATTACK_CHOICES, ATTACK_KEYS, MOVE_KEYS, Avatar, Villain, resolve_score_duel
    from .background import Background
    from .board import Board
    from .impact_screen import ImpactScreen
    from .pixel_art import CanvasConfig, PixelArt
except ImportError:  # pragma: no cover - script import fallback
    from avatar import ATTACK_CHOICES, ATTACK_KEYS, MOVE_KEYS, Avatar, Villain, resolve_score_duel
    from background import Background
    from board import Board
    from impact_screen import ImpactScreen
    from pixel_art import CanvasConfig, PixelArt


class BeastBoardGame:
    """Main game coordinator."""

    MAX_LEVEL = 5

    def __init__(self, *, seed: int = 1337) -> None:
        self._rng = random.Random(seed)
        self._canvas = CanvasConfig()
        self._pixel_art = PixelArt(self._canvas)
        self._board = Board(self._canvas)
        self._background = Background(self._pixel_art)
        self._impact = ImpactScreen(self._pixel_art)

        self._hud_height = 120
        canvas_w, canvas_h = self._canvas.canvas_size
        self.window_size = (canvas_w, canvas_h + self._hud_height)
        self._screen = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption("BeastBoard")

        self._font = pygame.font.SysFont("consolas", 18)
        self._small_font = pygame.font.SysFont("consolas", 16)

        self.avatar = Avatar("Hero", self._board.width // 2, self._board.height // 2, pixel_art=self._pixel_art)
        self.level = 1
        self.level_defeats = 0
        self.door_required = 0
        self.door_open = False
        self.door_pos: tuple[int, int] | None = None
        self.villains: list[Villain] = []
        self.running = True
        self.game_over = False
        self.victory = False

        self.pending_level_choice: int | None = None
        self.pending_redo: dict[str, object] | None = None
        self.pending_advance = False

        self.last_message = ""
        self.last_details = ""
        self.boss_impervious_hint = ""

        self._start_level(1, reset_avatar=True)

    def _door_threshold(self, level: int) -> int:
        return 3 + (level * 2)

    def _villain_count(self, level: int) -> int:
        if level >= self.MAX_LEVEL:
            return 1
        return min(12, 4 + (level * 2))

    def _free_cells(self) -> list[tuple[int, int]]:
        cells: list[tuple[int, int]] = []
        ax, ay = self.avatar.position
        for y in range(self._board.height):
            for x in range(self._board.width):
                if (x, y) == (ax, ay):
                    continue
                if self._board.is_occupied(x, y):
                    continue
                cells.append((x, y))
        return cells

    def _spawn_villains(self) -> list[Villain]:
        spawned: list[Villain] = []
        count = self._villain_count(self.level)
        free = self._free_cells()
        self._rng.shuffle(free)

        if self.level == self.MAX_LEVEL:
            bx, by = free[0]
            boss = Villain(
                "Boss",
                bx,
                by,
                level=self.level,
                variant_index=0,
                pixel_art=self._pixel_art,
                rng=self._rng,
                is_boss=True,
            )
            boss.place_on_board(self._board)
            spawned.append(boss)
            return spawned

        for idx in range(min(count, len(free))):
            vx, vy = free[idx]
            villain = Villain(
                f"Villain-{idx + 1}",
                vx,
                vy,
                level=self.level,
                variant_index=idx,
                pixel_art=self._pixel_art,
                rng=self._rng,
            )
            villain.place_on_board(self._board)
            spawned.append(villain)

        return spawned

    def _start_level(self, level: int, *, reset_avatar: bool = False) -> None:
        self.level = level
        self.level_defeats = 0
        self.door_required = self._door_threshold(level)
        self.door_open = False
        self.door_pos = None
        self.pending_advance = False
        self.pending_redo = None
        self.boss_impervious_hint = ""

        self._board = Board(self._canvas)
        self._background.set_level(level)

        if reset_avatar:
            self.avatar = Avatar("Hero", self._board.width // 2, self._board.height // 2, pixel_art=self._pixel_art)
        else:
            self.avatar.set_position(self._board.width // 2, self._board.height // 2)
            self.avatar.revive()

        self.avatar.place_on_board(self._board)
        self.villains = self._spawn_villains()

        self.last_message = f"Level {self.level} started"
        self.last_details = ""

    def restart(self) -> None:
        self.game_over = False
        self.victory = False
        self.pending_level_choice = None
        self._start_level(1, reset_avatar=True)

    def _open_door_if_ready(self) -> None:
        if self.door_open or self.level_defeats < self.door_required:
            return

        choices = [cell for cell in self._free_cells() if cell != self.avatar.position]
        if not choices:
            return
        self.door_pos = self._rng.choice(choices)
        self.door_open = True
        self._impact.activate("door_ready")
        self.last_message = "Door unlocked! Enter the yellow square to advance."

    def _adjacent_positions(self, x: int, y: int) -> Iterable[tuple[int, int]]:
        yield x, y - 1
        yield x + 1, y
        yield x, y + 1
        yield x - 1, y

    def _villain_at(self, pos: tuple[int, int]) -> Villain | None:
        for villain in self.villains:
            if villain.visible and villain.position == pos:
                return villain
        return None

    def _adjacent_villains(self, center: tuple[int, int], *, exclude: Villain | None = None) -> list[Villain]:
        cx, cy = center
        result: list[Villain] = []
        for pos in self._adjacent_positions(cx, cy):
            target = self._villain_at(pos)
            if target is None:
                continue
            if exclude is not None and target is exclude:
                continue
            result.append(target)
        return result

    def _select_attack_target(self) -> Villain | None:
        adjacent = self._adjacent_villains(self.avatar.position)
        if adjacent:
            target = adjacent[0]
            self.avatar.current_target_id = id(target)
            return target

        for villain in self.villains:
            if villain.visible and id(villain) == self.avatar.current_target_id:
                return villain

        alive = [v for v in self.villains if v.visible]
        if not alive:
            return None

        ax, ay = self.avatar.position
        alive.sort(key=lambda v: (abs(v.position[0] - ax) + abs(v.position[1] - ay), v.position[1], v.position[0]))
        target = alive[0]
        self.avatar.current_target_id = id(target)
        return target

    def _handle_level_up_input(self, key: int) -> bool:
        if self.pending_level_choice in (2, 3):
            choice = ATTACK_KEYS.get(key)
            if choice is None:
                return False
            applied = self.avatar.apply_level_up(self.pending_level_choice, choice)
            if applied:
                self._impact.activate("level_up")
                self.pending_level_choice = None
                self.last_message = "Level up applied"
                self.last_details = f"Choice {choice} upgraded"
            return applied

        if key not in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            return False

        option = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4}[key]
        if option in (2, 3):
            self.pending_level_choice = option
            self.last_message = "Choose attack key Y/U/I/O/P"
            self.last_details = ""
            return True

        applied = self.avatar.apply_level_up(option)
        if applied:
            self._impact.activate("level_up")
            self.last_message = "Level up applied"
            self.last_details = f"Option {option}"
        return applied

    def _enter_door(self) -> None:
        self._impact.activate("door_enter", long=True)
        self.pending_advance = True
        self.last_message = "Entering door..."

    def _after_impact_actions(self) -> None:
        if self.pending_advance and not self._impact.is_active:
            self.pending_advance = False
            if self.level < self.MAX_LEVEL:
                self._start_level(self.level + 1)
            else:
                self.victory = True
                self.game_over = True
                self.last_message = "Victory! Press R to restart."

    def _combat_support(self, primary: Villain, primary_choice: str) -> tuple[int, int, int, list[Villain], list[str]]:
        supporters = self._adjacent_villains(primary.position, exclude=primary)
        if self.level < 3 or not supporters or primary.is_boss:
            return 0, 0, 0, [], []

        base_boost = 0
        win_boost = 0
        loss_boost = 0
        joiners: list[Villain] = []
        events: list[str] = []

        for helper in supporters:
            action = self._rng.choice(("base", "win", "loss", "join"))
            if action == "base":
                base_boost += 1
                events.append(f"{helper.name} boosted base")
            elif action == "win":
                win_boost += 2
                events.append(f"{helper.name} boosted win")
            elif action == "loss":
                loss_boost += 1
                events.append(f"{helper.name} boosted loss")
            else:
                joiners.append(helper)
                events.append(f"{helper.name} joined attack")

        return base_boost, win_boost, loss_boost, joiners, events

    def _apply_avatar_loss(self, context: dict[str, object], *, allow_redo: bool) -> None:
        if allow_redo and self.avatar.redo_charges > 0:
            self.pending_redo = context
            self.last_message = "Pre-death redo: choose Y/U/I/O/P"
            self.last_details = "Redo will be consumed on use"
            return

        self.avatar.begin_death()
        self._impact.activate("avatar_death", long=True)
        self.game_over = True
        self.last_message = "You died. Press R to restart."

    def _resolve_round(self, primary: Villain, avatar_choice: str, *, allow_redo: bool) -> None:
        if not primary.visible:
            return

        primary_choice = primary.choose_combat_choice()
        impervious = None
        if primary.is_boss:
            impervious = self._rng.choice(ATTACK_CHOICES)
            self.boss_impervious_hint = f"Boss impervious this round: {impervious}"

        base_boost, win_boost, loss_boost, joiners, support_events = self._combat_support(primary, primary_choice)
        participants = [primary] + [joiner for joiner in joiners if joiner.visible]

        duels = []
        for idx, villain in enumerate(participants):
            choice = primary_choice if idx == 0 else villain.choose_combat_choice()
            duel = resolve_score_duel(
                avatar_choice=avatar_choice,
                enemy_choice=choice,
                avatar_base_attack=self.avatar.base_attack,
                enemy_base_attack=villain.base_attack + (base_boost if idx == 0 else 0),
                avatar_win_modifier=self.avatar.win_modifiers[avatar_choice],
                avatar_loss_modifier=self.avatar.loss_modifiers[avatar_choice],
                enemy_win_modifier=villain.win_modifiers[choice] + (win_boost if idx == 0 else 0),
                enemy_loss_modifier=villain.loss_modifiers[choice] + (loss_boost if idx == 0 else 0),
                enemy_impervious_choice=impervious if idx == 0 and primary.is_boss else None,
            )
            duels.append((villain, duel))

        primary_duel = duels[0][1]
        avatar_anchor_score = primary_duel.avatar_score
        combined_enemy_score = sum(duel.enemy_score for _, duel in duels)
        defeated = [villain for villain, duel in duels if avatar_anchor_score > duel.enemy_score]

        avatar_loses = combined_enemy_score >= avatar_anchor_score and not defeated

        if defeated:
            defeated_count = 0
            for villain in defeated:
                if villain.lose_life():
                    defeated_count += 1
                elif villain.is_boss:
                    self._impact.activate("boss_damage")
            if defeated_count:
                gained = self.avatar.register_defeat(defeated_count)
                self.level_defeats += defeated_count
                if primary.is_boss and not primary.visible:
                    self._impact.activate("final_kill", long=True)
                    self.victory = True
                    self.game_over = True
                    self.last_message = "Boss defeated! Press R to restart."
                else:
                    self.last_message = f"Defeated {defeated_count} enemy"
                    self.last_details = f"You {avatar_anchor_score} vs enemy total {combined_enemy_score}"
                    if gained:
                        self.last_details = f"Level-up choices gained: {gained}"
                    if not any(v.visible for v in self.villains):
                        self._impact.activate("final_kill", long=True)
                self._open_door_if_ready()

        if avatar_loses and not self.game_over:
            self._apply_avatar_loss(
                {
                    "primary": primary,
                    "primary_choice": primary_choice,
                    "support_events": support_events,
                },
                allow_redo=allow_redo,
            )
            return

        self.avatar.set_state("attack")
        detail = f"{avatar_choice}:{avatar_anchor_score} vs {primary_choice}:{primary_duel.enemy_score}"
        if primary_duel.impervious_blocked:
            detail += " | impervious blocked win bonus"
        if support_events:
            detail += " | " + "; ".join(support_events)
        self.last_details = detail

    def _handle_movement(self, dx: int, dy: int, facing: str) -> None:
        if self.game_over:
            return

        ax, ay = self.avatar.position
        target = (ax + dx, ay + dy)
        tx, ty = target
        if not self._board.in_bounds(tx, ty):
            return

        if self.door_open and self.door_pos == target:
            self.avatar.move(dx, dy, self._board, facing=facing)
            self._enter_door()
            return

        villain = self._villain_at(target)
        if villain is not None:
            self.avatar.set_state("attack")
            self._resolve_round(villain, self.avatar.queued_attack_choice, allow_redo=True)
            return

        self.avatar.move(dx, dy, self._board, facing=facing)

    def _handle_attack(self, choice: str, *, allow_redo: bool = True) -> None:
        self.avatar.set_attack_choice(choice)
        target = self._select_attack_target()
        if target is None:
            self.last_message = "No target"
            self.last_details = "Move adjacent or acquire target"
            self.avatar.set_state("attack")
            return

        self._resolve_round(target, choice, allow_redo=allow_redo)

    def _handle_redo_input(self, key: int) -> bool:
        if self.pending_redo is None:
            return False
        choice = ATTACK_KEYS.get(key)
        if choice is None:
            return False

        primary = self.pending_redo.get("primary")
        if not isinstance(primary, Villain) or not primary.visible:
            self.pending_redo = None
            self.last_message = "Redo target no longer available"
            return False

        self.avatar.redo_charges -= 1
        self.pending_redo = None
        self.last_message = "Redo used"
        self._resolve_round(primary, choice, allow_redo=False)
        return True

    def handle_key(self, key: int) -> None:
        if key == pygame.K_r and self.game_over:
            self.restart()
            return

        if self.game_over:
            return

        if self._impact.is_active and self.pending_advance:
            return

        if self.pending_redo is not None:
            self._handle_redo_input(key)
            return

        if self.avatar.pending_level_ups > 0:
            self._handle_level_up_input(key)
            return

        move = MOVE_KEYS.get(key)
        if move is not None:
            self._handle_movement(*move)
            return

        attack = ATTACK_KEYS.get(key)
        if attack is not None:
            self._handle_attack(attack)

    def _update_entities(self) -> None:
        self.avatar.update(self._board)
        for villain in self.villains:
            villain.update(self._board)
        self.villains = [villain for villain in self.villains if villain.visible]

    def update(self) -> None:
        self._impact.update()
        self._after_impact_actions()
        self._update_entities()

    def _draw_door(self) -> None:
        if not self.door_open or self.door_pos is None:
            return
        px, py = self._board.to_pixel(*self.door_pos)
        rect = pygame.Rect(px + 3, py + 3, self._board.cell_size - 6, self._board.cell_size - 6)
        pygame.draw.rect(self._screen, (240, 210, 40), rect)
        pygame.draw.rect(self._screen, (40, 30, 0), rect, 2)

    def _draw_hud(self) -> None:
        canvas_h = self._canvas.canvas_size[1]
        hud_rect = pygame.Rect(0, canvas_h, self.window_size[0], self._hud_height)
        self._screen.fill((248, 248, 248), hud_rect)

        lines = [
            f"Level {self.level}/5 | Defeats this level: {self.level_defeats}/{self.door_required}",
            f"Avatar Lvl {self.avatar.level} | Base {self.avatar.base_attack} | Redo {self.avatar.redo_charges}",
            "Move: W A S D   Attack: Y U I O P",
        ]

        if self.boss_impervious_hint and any(v.is_boss for v in self.villains):
            lines.append(self.boss_impervious_hint)
        if self.last_message:
            lines.append(self.last_message)
        if self.last_details:
            lines.append(self.last_details)

        y = canvas_h + 8
        for text in lines[:6]:
            surf = self._small_font.render(text, True, (0, 0, 0))
            self._screen.blit(surf, (10, y))
            y += 18

    def _draw_level_up_overlay(self) -> None:
        if self.avatar.pending_level_ups <= 0:
            return

        box = pygame.Rect(80, 180, 480, 250)
        pygame.draw.rect(self._screen, (255, 255, 255), box)
        pygame.draw.rect(self._screen, (0, 0, 0), box, 3)
        lines = [
            f"Level Up! Remaining choices: {self.avatar.pending_level_ups}",
            "1) +1 base attack",
            "2) +2 win modifier for one attack (then press Y/U/I/O/P)",
            "3) +1 loss modifier for one attack (then press Y/U/I/O/P)",
            "4) Grant one pre-death redo",
        ]

        y = box.y + 18
        for text in lines:
            surf = self._font.render(text, True, (0, 0, 0))
            self._screen.blit(surf, (box.x + 16, y))
            y += 40

        if self.pending_level_choice in (2, 3):
            sub = self._font.render("Choose attack key now: Y/U/I/O/P", True, (0, 0, 0))
            self._screen.blit(sub, (box.x + 16, box.bottom - 40))

    def _draw_death_overlay(self) -> None:
        if not self.game_over or self.victory:
            return
        rect = pygame.Rect(140, 260, 360, 110)
        pygame.draw.rect(self._screen, (255, 255, 255), rect)
        pygame.draw.rect(self._screen, (0, 0, 0), rect, 3)
        line1 = self._font.render("You died.", True, (0, 0, 0))
        line2 = self._font.render("Press R to restart.", True, (0, 0, 0))
        self._screen.blit(line1, (rect.x + 120, rect.y + 24))
        self._screen.blit(line2, (rect.x + 72, rect.y + 60))

    def _draw_victory_overlay(self) -> None:
        if not self.victory:
            return
        rect = pygame.Rect(120, 240, 400, 150)
        pygame.draw.rect(self._screen, (255, 255, 255), rect)
        pygame.draw.rect(self._screen, (160, 0, 0), rect, 4)
        line1 = self._font.render("Boss defeated!", True, (0, 0, 0))
        line2 = self._font.render("Press R to restart.", True, (0, 0, 0))
        self._screen.blit(line1, (rect.x + 120, rect.y + 38))
        self._screen.blit(line2, (rect.x + 108, rect.y + 82))

    def draw(self) -> None:
        self._background.draw(self._screen, self.level)
        self._draw_door()
        self._board.draw(self._screen)
        for villain in self.villains:
            villain.draw(self._screen, self._board)
        self.avatar.draw(self._screen, self._board)

        if self._impact.is_active:
            self._impact.draw(self._screen)

        self._draw_hud()
        self._draw_level_up_overlay()
        self._draw_death_overlay()
        self._draw_victory_overlay()

    def run(self, *, max_frames: int | None = None) -> None:
        clock = pygame.time.Clock()
        frame_count = 0

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)

            self.update()
            self.draw()
            pygame.display.flip()
            clock.tick(60)

            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                self.running = False


def run(*, max_frames: int | None = None, headless: bool = False) -> None:
    """Run the game loop."""

    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    try:
        game = BeastBoardGame()
        game.run(max_frames=max_frames)
    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
