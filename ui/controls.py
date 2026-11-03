import pygame

from game.world import World
from game.i18n import T, LANGUAGES, get_language, set_language
from ui.widgets import Button, Switch, Segmented, Stepper


class ControlPanel:
    """Bottom bar: agent, dungeon, manual control and view settings."""

    def __init__(self, rect, gm, renderer, sound_manager, dev_panel=None):
        self.rect = pygame.Rect(rect)
        self.gm = gm
        self.renderer = renderer
        self.sound = sound_manager
        self.shoot_mode = False

        x0, y0 = self.rect.x, self.rect.y
        row1, row2 = y0 + 40, y0 + 84
        playing = lambda: not gm.game_over

        # name, x, width
        self.groups = [(T("group.agent"), x0 + 24), (T("group.dungeon"), x0 + 308),
                       (T("group.manual"), x0 + 636), (T("group.view"), x0 + 968)]

        ax = x0 + 24
        mx = x0 + 308
        hx = x0 + 636
        vx = x0 + 968

        self.widgets = [
            # Agent
            Button((ax, row1, 96, 32), T("btn.step"), gm.step_ai, kind="primary", enabled=playing),
            Switch((ax + 116, row1 + 5), T("sw.auto"), lambda: gm.auto_mode, self._set_auto, enabled=playing),
            Segmented((ax, row2, 248, 32), [("slow", T("speed.slow")), ("normal", T("speed.normal")), ("fast", T("speed.fast"))],
                      lambda: gm.speed, lambda v: setattr(gm, "speed", v)),
            # Dungeon
            Button((mx, row1, 100, 32), T("btn.new_map"), lambda: gm.reset("random"), kind="primary"),
            Button((mx + 108, row1, 92, 32), T("btn.replay"), lambda: gm.reset("replay")),
            Button((mx + 208, row1, 92, 32), T("btn.classic"), lambda: gm.reset("classic")),
            Stepper((mx + 108, row2, 120, 32), lambda: gm.num_rooms, gm.set_num_rooms,
                    World.MIN_ROOMS, World.MAX_ROOMS),
            # Manual control: inverted-T arrow pad
            Button((hx + 36, row1, 32, 32), "", lambda: self._direction("UP"), icon="UP", enabled=playing),
            Button((hx, row2 - 8, 32, 32), "", lambda: self._direction("LEFT"), icon="LEFT", enabled=playing),
            Button((hx + 36, row2 - 8, 32, 32), "", lambda: self._direction("DOWN"), icon="DOWN", enabled=playing),
            Button((hx + 72, row2 - 8, 32, 32), "", lambda: self._direction("RIGHT"), icon="RIGHT", enabled=playing),
            Switch((hx + 124, row1 + 5), T("sw.shoot"), lambda: self.shoot_mode, self._set_shoot,
                   enabled=lambda: playing() and gm.agent.has_arrow),
            Button((hx + 124, row2 - 8, 176, 32), T("btn.grab"), gm.manual_grab, enabled=playing),
            # View
            Switch((vx, row1 + 2), T("sw.dark"), lambda: renderer.dark, renderer.set_dark, width=168),
            Switch((vx, row1 + 30), T("sw.sound"), lambda: sound_manager.is_enabled, self._set_sound, width=168),
            Segmented((vx, row1 + 58, 168, 28), LANGUAGES, get_language, set_language),
            # "Reveal map" sits in the room card header, next to the board it changes
            Switch((renderer.game_rect.right - 24 - 136, renderer.game_rect.y + 17), T("sw.reveal"),
                   lambda: renderer.reveal_all, lambda v: setattr(renderer, "reveal_all", v), width=136),
        ]
        if dev_panel:
            # Lives in the Agent card header, next to the title
            info = renderer.info_rect
            self.widgets.append(Button((info.x + 100, info.y + 16, 92, 24), T("btn.analytics"), dev_panel.toggle))
        self.rooms_label_pos = (mx, row2 + 16)

    def _set_auto(self, value):
        self.gm.auto_mode = value

    def _set_shoot(self, value):
        self.shoot_mode = value

    def _set_sound(self, value):
        self.sound.is_enabled = value
        if not value:
            self.sound.stop_all()

    def _direction(self, direction):
        if self.shoot_mode:
            self.gm.manual_shoot(direction)
            self.shoot_mode = False
        else:
            dr, dc = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}[direction]
            self.gm.manual_move(dr, dc)

    def handle(self, event):
        consumed = False
        for w in self.widgets:
            consumed = w.handle(event) or consumed
        return consumed

    def hovering(self, pos):
        return any(w.hit(pos) and w.enabled for w in self.widgets)

    def draw(self, p):
        t = p.theme
        for i, (name, gx) in enumerate(self.groups):
            p.text(str(name).upper(), (gx, self.rect.y + 22), 11, t["text3"], "medium", anchor="midleft")
            if i:
                x = gx - 20
                p.line((x, self.rect.y + 20), (x, self.rect.bottom - 20), t["border"])
        p.text(T("label.rooms"), self.rooms_label_pos, 14, t["text2"], anchor="midleft")
        for w in self.widgets:
            w.draw(p)
