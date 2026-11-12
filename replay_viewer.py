"""
Replay viewer: lists the last saved games and plays any of them back.

Run: python3 replay_viewer.py   (or the Replays button / F2 in the game window)

Games are saved by main.py when they end (see game/replays.py). A replay runs the
recorded actions on a fresh GameManager and draws it with the game's own Renderer.
"""
from datetime import datetime

import pygame

from game.game_manager import GameManager
from game.i18n import T, tr, LANGUAGES, get_language, set_language, algorithm_label
from game.replays import ReplayStore, Replay, MAX_GAMES
from main import create_window
from ui.renderer import Renderer, WINDOW_SIZE
from ui.widgets import Widget, Button, Switch, Segmented

RELOAD_EVERY_MS = 1000  # the game may save new games while the viewer is open


# ----------------------------------------------------------------------
# Game info shown in the list and in the player
# ----------------------------------------------------------------------
def when(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d  %H:%M:%S")
    except (TypeError, ValueError):
        return "-"


def mode_label(record):
    return tr(f"control.{record.get('control', 'ai')}", algo=algorithm_label(record["algorithm"]))


def map_label(record):
    if record.get("map") == "classic":
        return tr("rv.map.classic")
    rooms = record.get("rooms", 1)
    return tr("rv.map.random1") if rooms == 1 else tr("rv.map.random", n=rooms)


def outcome_colors(t, outcome):
    if outcome == "win":
        return t["success"], t["success_light"]
    if outcome in ("pit", "wumpus"):
        return t["danger"], t["danger_light"]
    return t["warning"], t["warning_light"]


# ----------------------------------------------------------------------
# Game list
# ----------------------------------------------------------------------
class ListScreen:
    HEADER = pygame.Rect(20, 20, 1160, 84)
    TABLE = pygame.Rect(20, 120, 1160, 660)
    ROW_H = 56
    # column key, x
    COLUMNS = [("game", 44), ("when", 84), ("mode", 264), ("map", 494), ("result", 694),
               ("score", 864), ("steps", 944), ("duration", 1014), ("moves", 1094)]

    def __init__(self, viewer):
        self.viewer = viewer
        r = self.HEADER
        self.widgets = [
            Switch((r.right - 24 - 168 - 16 - 130, r.centery - 11), T("sw.dark"),
                   lambda: viewer.renderer.dark, viewer.renderer.set_dark, width=130),
            Segmented((r.right - 24 - 168, r.centery - 14, 168, 28), LANGUAGES, get_language, set_language),
        ]
        self.rows = []  # (rect, index) of the drawn rows
        self.hover_row = None

    def handle(self, event):
        consumed = any([w.handle(event) for w in self.widgets])
        if event.type == pygame.MOUSEMOTION:
            self.hover_row = next((i for rect, i in self.rows if rect.collidepoint(event.pos)), None)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not consumed:
            for rect, i in self.rows:
                if rect.collidepoint(event.pos):
                    self.viewer.open(i)
                    return True
        elif event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_9:
                self.viewer.open(event.key - pygame.K_1)
            elif event.key == pygame.K_0:
                self.viewer.open(9)
        return consumed

    def hovering(self, pos):
        return self.hover_row is not None or any(w.hit(pos) for w in self.widgets)

    def draw(self, p):
        t = p.theme
        games = self.viewer.games
        p.screen.fill(t["bg"])
        for rect in (self.HEADER, self.TABLE):
            p.box(rect, t["card"], radius=8, border=t["border"])

        h = self.HEADER
        p.text(tr("rv.title"), (h.x + 24, h.y + 30), 20, t["text1"], "bold", anchor="midleft")
        p.text(tr("rv.subtitle", n=MAX_GAMES), (h.x + 24, h.y + 58), 13, t["text3"], anchor="midleft")
        for w in self.widgets:
            w.draw(p)

        r = self.TABLE
        self.rows = []
        if not games:
            p.text(tr("rv.empty"), (r.centerx, r.centery - 14), 18, t["text1"], "bold", anchor="center")
            p.text(tr("rv.empty_hint"), (r.centerx, r.centery + 14), 14, t["text3"], anchor="center")
            return

        y = r.y + 28
        for key, x in self.COLUMNS:
            p.text(tr(f"rcol.{key}"), (x, y), 12, t["text3"], "medium", anchor="midleft")
        y += 20
        p.line((r.x + 16, y), (r.right - 16, y), t["border"])
        y += 6

        for i, record in enumerate(games):
            row = pygame.Rect(r.x + 8, y, r.width - 16, self.ROW_H - 4)
            self.rows.append((row, i))
            if i == self.hover_row:
                p.box(row, t["fill2"], radius=6)
            cy = row.centery
            res = record.get("result", {})
            fg, bg = outcome_colors(t, res.get("outcome"))
            col = dict(self.COLUMNS)

            p.circle((col["game"] + 10, cy), 13, t["primary_light"])
            p.text(str(i + 1), (col["game"] + 10, cy), 13, t["primary"], "bold", anchor="center")
            p.text(when(record.get("started_at")), (col["when"], cy), 13, t["text1"], "medium", anchor="midleft")
            p.text(mode_label(record), (col["mode"], cy), 13, t["text1"], anchor="midleft")
            p.text(map_label(record), (col["map"], cy - (8 if record.get("retry") else 0)), 13, t["text2"], anchor="midleft")
            if record.get("retry"):
                p.text(tr("btn.replay"), (col["map"], cy + 10), 11, t["text3"], anchor="midleft")
            p.tag(tr(f"outcome.{res.get('outcome') or 'none'}"), (col["result"], cy), fg, bg, anchor="midleft")
            p.text(str(res.get("score", "-")), (col["score"], cy), 14, t["text1"], "bold", anchor="midleft")
            p.text(str(res.get("steps", "-")), (col["steps"], cy), 13, t["text1"], anchor="midleft")
            p.text(tr("rv.duration", s=f"{res.get('duration_s', 0):.1f}"), (col["duration"], cy), 13, t["text1"], anchor="midleft")
            p.text(str(len(record.get("events", []))), (col["moves"], cy), 13, t["text1"], anchor="midleft")
            y += self.ROW_H

        p.text(tr("rv.open_hint"), (r.x + 24, r.bottom - 22), 12, t["text3"], anchor="midleft")


# ----------------------------------------------------------------------
# Player
# ----------------------------------------------------------------------
class Timeline(Widget):
    """Progress bar of the replay; click or drag to jump to any action."""

    def __init__(self, rect, player):
        super().__init__(rect)
        self.player = player
        self.dragging = False

    def _track(self):
        return pygame.Rect(self.rect.x + 8, self.rect.centery - 3, self.rect.width - 16, 6)

    def _seek(self, x):
        track = self._track()
        frac = min(1.0, max(0.0, (x - track.x) / track.width))
        self.player.seek(round(frac * self.player.replay.length))

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.hit(event.pos)
            if self.dragging:
                self._seek(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hit(event.pos):
            self.dragging = True
            self._seek(event.pos[0])
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            return True
        return False

    def draw(self, p):
        t = p.theme
        replay = self.player.replay
        track = self._track()
        p.box(track, t["fill3"], radius=3)
        frac = replay.position / replay.length if replay.length else 1.0
        done = pygame.Rect(track.x, track.y, max(6, round(track.width * frac)), track.height)
        p.box(done, t["primary"], radius=3)
        knob = (track.x + round(track.width * frac), track.centery)
        p.circle(knob, 8 if self.hover or self.dragging else 7, t["primary"])
        p.circle(knob, 4, t["card"])


class PlayerScreen:
    """The game's own screen with a playback bar in place of the game controls."""

    def __init__(self, viewer, record, number):
        self.viewer = viewer
        self.record = record
        self.number = number
        self.replay = Replay(record)
        self.playing = True
        self.speed = "normal"
        self.last_step = pygame.time.get_ticks()

        renderer = viewer.renderer
        renderer.reveal_all = True  # a replay is for seeing why things happened
        renderer.view_room = None
        self.rect = renderer.bar_rect
        x0, y0 = self.rect.x, self.rect.y
        row1, row2 = y0 + 40, y0 + 84
        px, vx = x0 + 520, x0 + 968
        self.groups = [(T("group.game"), x0 + 24), (T("group.playback"), px), (T("group.view"), vx)]
        self.counter_pos = (px + 408, row1 + 16)

        self.play_button = Button((px + 100, row1, 80, 32), "", self.toggle, kind="primary")
        self.play_button.hotkey = "Space"
        self.widgets = [
            Button((px, row1, 56, 32), T("btn.start"), lambda: self.seek(0)),
            Button((px + 62, row1, 32, 32), "", lambda: self.step(-1), icon="LEFT"),
            self.play_button,
            Button((px + 186, row1, 32, 32), "", lambda: self.step(1), icon="RIGHT"),
            Button((px + 224, row1, 56, 32), T("btn.end"), lambda: self.seek(self.replay.length)),
            Timeline((px - 8, row2, 244, 32), self),
            Segmented((px + 240, row2, 168, 32), [("slow", T("speed.slow")), ("normal", T("speed.normal")),
                                                  ("fast", T("speed.fast"))],
                      lambda: self.speed, lambda v: setattr(self, "speed", v)),
            Button((vx, y0 + 36, 168, 30), T("btn.back"), viewer.close, kind="primary"),
            Switch((vx, y0 + 76), T("sw.dark"), lambda: renderer.dark, renderer.set_dark, width=168),
            Segmented((vx, y0 + 102, 168, 28), LANGUAGES, get_language, set_language),
            Switch((renderer.game_rect.right - 24 - 136, renderer.game_rect.y + 17), T("sw.reveal"),
                   lambda: renderer.reveal_all, lambda v: setattr(renderer, "reveal_all", v), width=136),
        ]
        for widget, key in zip(self.widgets[:5], ("Home", "←", None, "→", "End")):
            widget.hotkey = key or widget.hotkey
        self.widgets[7].hotkey = "Esc"

    # Playback -----------------------------------------------------------
    def toggle(self):
        if self.replay.at_end:
            self.seek(0)
        self.playing = not self.playing
        self.last_step = pygame.time.get_ticks()

    def seek(self, position):
        self.playing = False
        self.replay.seek(position)

    def step(self, delta):
        self.seek(self.replay.position + delta)

    def update(self, now):
        if self.playing and now - self.last_step >= GameManager.SPEEDS[self.speed]:
            self.replay.step()
            self.last_step = now
            if self.replay.at_end:
                self.playing = False

    # Events -------------------------------------------------------------
    def handle(self, event):
        renderer = self.viewer.renderer
        if event.type == pygame.KEYDOWN:
            keys = {
                pygame.K_SPACE: self.toggle,
                pygame.K_LEFT: lambda: self.step(-1),
                pygame.K_RIGHT: lambda: self.step(1),
                pygame.K_HOME: lambda: self.seek(0),
                pygame.K_END: lambda: self.seek(self.replay.length),
                pygame.K_TAB: lambda: setattr(renderer, "reveal_all", not renderer.reveal_all),
            }
            if event.key in keys:
                keys[event.key]()
                return True
            return False
        consumed = False
        for w in self.widgets:
            consumed = w.handle(event) or consumed
        if not consumed and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            consumed = renderer.handle_click(event.pos)
        return consumed

    def hovering(self, pos):
        return any(w.hit(pos) and w.enabled for w in self.widgets) or self.viewer.renderer.minimap_hover(pos)

    # Drawing (called by Renderer.draw as its control bar) ----------------
    def draw(self, p):
        t = p.theme
        record, res = self.record, self.record.get("result", {})
        renderer = self.viewer.renderer
        x0, y0 = self.rect.x, self.rect.y

        for i, (name, gx) in enumerate(self.groups):
            p.text(str(name).upper(), (gx, y0 + 22), 11, t["text3"], "medium", anchor="midleft")
            if i:
                p.line((gx - 20, y0 + 20), (gx - 20, self.rect.bottom - 20), t["border"])

        # Game info
        gx = x0 + 24
        title = p.text(tr("rv.game_n", n=self.number), (gx, y0 + 52), 16, t["text1"], "bold", anchor="midleft")
        p.text(tr("rv.started", when=when(record.get("started_at"))), (title.right + 12, y0 + 52), 13, t["text3"],
               anchor="midleft")
        mode = f"{mode_label(record)}   ·   {map_label(record)}"
        if record.get("retry"):
            mode += f"   ·   {tr('rv.retry')}"
        p.text(mode, (gx, y0 + 80), 13, t["text2"], anchor="midleft")
        fg, bg = outcome_colors(t, res.get("outcome"))
        tag = p.tag(tr(f"outcome.{res.get('outcome') or 'none'}"), (gx, y0 + 110), fg, bg, anchor="midleft")
        stats = tr("rv.stats", score=res.get("score", "-"), steps=res.get("steps", "-"), shots=res.get("shots", 0),
                   explored=f"{res.get('explored', 0):.0%}")
        stats += "  ·  " + tr("rv.duration", s=f"{res.get('duration_s', 0):.1f}")
        p.text(stats, (tag.right + 12, y0 + 110), 13, t["text1"], anchor="midleft")

        # Playback
        self.play_button.label = T("btn.pause" if self.playing else "btn.play")
        p.text(tr("rv.action", i=self.replay.position, n=self.replay.length), self.counter_pos, 13, t["text2"],
               "medium", anchor="midright")
        for w in self.widgets:
            w.draw(p)

        # The algorithm sits where the game has its algorithm switcher
        m = renderer.map_rect
        p.tag(str(algorithm_label(record["algorithm"])), (m.right - 20, m.y + 28), t["primary"], t["primary_light"],
              anchor="midright")


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------
class Viewer:
    def __init__(self, screen):
        self.renderer = Renderer(screen)
        self.renderer.result_hint = "result.replay_hint"
        self.store = ReplayStore()
        self.games = []
        self._loaded_mtime = object()
        self.reload()
        self.list = ListScreen(self)
        self.player = None

    def reload(self):
        mtime = self.store.modified()
        if mtime != self._loaded_mtime:
            self._loaded_mtime = mtime
            self.games = self.store.load()

    def open(self, index):
        if 0 <= index < len(self.games):
            try:
                self.player = PlayerScreen(self, self.games[index], index + 1)
            except (KeyError, TypeError, ValueError) as e:
                print(f"Could not open game #{index + 1}: {e}")

    def close(self):
        self.player = None
        self.reload()

    @property
    def screen(self):
        return self.player or self.list

    def draw(self):
        if self.player:
            self.renderer.draw(self.player.replay.gm, self.player)
        else:
            self.list.draw(self.renderer.p)


def main():
    pygame.init()
    screen, show_frame = create_window("Wumpus World - Replays")
    clock = pygame.time.Clock()
    viewer = Viewer(screen)
    last_reload = 0
    running = True

    while running:
        now = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if viewer.player:
                        viewer.close()
                    else:
                        running = False
                    continue
                if event.key == pygame.K_t:
                    viewer.renderer.set_dark(not viewer.renderer.dark)
                    continue
                if event.key == pygame.K_l:
                    set_language("ko" if get_language() == "en" else "en")
                    continue
            viewer.screen.handle(event)
            if event.type == pygame.MOUSEMOTION:
                hand = viewer.screen.hovering(event.pos)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW)

        if viewer.player:
            viewer.player.update(now)
        elif now - last_reload >= RELOAD_EVERY_MS:
            viewer.reload()
            last_reload = now

        viewer.draw()
        show_frame()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
