"""
Pygame renderer with an Arco-style layout:
- top left: the room the agent is in (pixel-art board)
- top right: dungeon minimap and the agent panel (stats, percepts, reasoning, log)
- bottom: control bar (see ui/controls.py)
"""
import pygame

from ui.painter import Painter
from ui.paths import asset
from ui.theme import LIGHT, DARK
from game.i18n import tr

WINDOW_SIZE = (1200, 800)


class Renderer:
    CELL = 124
    HINT = 30  # percept icon box

    def __init__(self, screen):
        self.screen = screen
        self.p = Painter(screen, WINDOW_SIZE[0])
        self.reveal_all = False
        self.view_room = None  # None = follow the agent; otherwise a room picked on the minimap
        self._followed = None

        self.game_rect = pygame.Rect(20, 20, 600, 600)
        self.map_rect = pygame.Rect(636, 20, 544, 272)
        self.info_rect = pygame.Rect(636, 308, 544, 312)
        self.bar_rect = pygame.Rect(20, 636, 1160, 144)
        board = self.CELL * 4
        self.board_rect = pygame.Rect(self.game_rect.x + (self.game_rect.width - board) // 2, 88, board, board)

        self._minimap_rooms = []
        self._shot_seen = None  # id of the arrow flight being animated
        self._shot_t0 = 0
        self._banner_room = None  # room whose number is shown after the agent enters it
        self._banner_t0 = 0
        self.assets = {}
        self._load_sprites()

    # ------------------------------------------------------------------
    # Theme / interaction
    # ------------------------------------------------------------------
    @property
    def dark(self):
        return self.p.theme is DARK

    def set_dark(self, value):
        self.p.theme = DARK if value else LIGHT

    def handle_click(self, pos):
        """Clicking a room on the minimap previews it; clicking the agent's room follows the agent again."""
        for rect, idx in self._minimap_rooms:
            if rect.collidepoint(pos):
                self.view_room = idx
                return True
        return False

    def minimap_hover(self, pos):
        return any(rect.collidepoint(pos) for rect, _ in self._minimap_rooms)

    def _load_sprites(self):
        c = self.CELL
        sizes = {
            "floor": (c - 4, c - 4),
            "door": (int(c * 0.44), int(c * 0.58)),
            "door_small": (int(c * 0.36), int(c * 0.47)),  # doors between rooms
            "hero": (int(c * 0.78),) * 2,
            "wumpus": (int(c * 0.78),) * 2,
            "pit": (c - 4, c - 4),  # the pit sprite is a full tile with its own floor
            "gold": (int(c * 0.6),) * 2,
            "scream": (int(c * 0.5),) * 2,
        }
        for name, size in sizes.items():
            path = asset(f"{name.replace('_small', '')}.png")
            key = "glitter" if name == "giltter" else name
            try:
                img = pygame.image.load(path)
                try:
                    img = img.convert_alpha()
                except pygame.error:
                    pass  # no display mode yet (pygame-ce Window); PNG alpha is kept as is
                self.assets[key] = self.p.scale_image(img, size)
            except (pygame.error, FileNotFoundError) as e:
                print(f"Error loading {path}: {e}")
                self.assets[key] = None

        # Percept icons: cropped to their drawn content so they all look the same size
        for key, name in (("breeze", "breeze"), ("stench", "scream"), ("glitter", "giltter")):
            path = asset(f"{name}.png")
            try:
                img = pygame.image.load(path)
                img = img.subsurface(img.get_bounding_rect(min_alpha=10)).copy()
                w, h = img.get_size()
                fit = min(self.HINT * 1.3 / w, self.HINT / h)  # wide icons may be a bit wider
                self.assets[key] = self.p.scale_image(img, (w * fit, h * fit))
            except (pygame.error, FileNotFoundError, ValueError) as e:
                print(f"Error loading {path}: {e}")
                self.assets[key] = None

        # Flying arrow: sprite points right, rotated copies for the other directions
        path = asset("arrow.png")
        try:
            img = pygame.image.load(path)
            img = img.subsurface(img.get_bounding_rect(min_alpha=10)).copy()
            w, h = img.get_size()
            length, thick = self.CELL * 0.45, self.CELL * 0.45 * h / w
            for direction, angle in (("RIGHT", 0), ("UP", 90), ("LEFT", 180), ("DOWN", -90)):
                size = (length, thick) if angle in (0, 180) else (thick, length)
                self.assets[f"arrow_{direction}"] = self.p.scale_image(pygame.transform.rotate(img, angle), size)
        except (pygame.error, FileNotFoundError, ValueError) as e:
            print(f"Error loading {path}: {e}")

    def _blit(self, key, **anchor):
        self.p.blit(self.assets.get(key), **anchor)

    # ------------------------------------------------------------------
    # Frame
    # ------------------------------------------------------------------
    def draw(self, gm, controls=None):
        t = self.p.theme
        world, agent = gm.world, gm.agent

        agent_room = world.room_of(agent.position)
        follow_key = (id(world.rooms), agent_room)
        # Same dungeon, new room, and not a fresh start: show the room number banner
        if self._followed and self._followed[0] == follow_key[0] and self._followed[1] != agent_room and gm.steps:
            self._banner_room, self._banner_t0 = agent_room, pygame.time.get_ticks()
        if follow_key != self._followed or (self.view_room is not None and self.view_room >= world.num_rooms):
            self.view_room = None
            self._followed = follow_key
        room = agent_room if self.view_room is None else self.view_room

        self.screen.fill(t["bg"])
        for rect in (self.game_rect, self.map_rect, self.info_rect, self.bar_rect):
            self.p.box(rect, t["card"], radius=8, border=t["border"])

        self._draw_game(gm, room, agent_room)
        self._draw_minimap(gm, room)
        self._draw_info(gm)
        if room == agent_room:
            self._draw_room_banner(gm, agent_room)
        if controls:
            controls.draw(self.p)
        if gm.game_over:
            self._draw_result(gm)

    # ------------------------------------------------------------------
    # Room view
    # ------------------------------------------------------------------
    def _draw_game(self, gm, room, agent_room):
        p, t = self.p, self.p.theme
        world, agent = gm.world, gm.agent
        x0, y0 = self.game_rect.x + 24, self.game_rect.y + 28

        title = p.text(tr("room.title", n=room + 1), (x0, y0), 18, t["text1"], "bold", anchor="midleft")
        of = p.text(tr("room.of", n=world.num_rooms), (title.right + 8, y0), 14, t["text3"], anchor="midleft")

        # Tags follow the title; the right side of the header holds the "Reveal map" switch
        tags = []
        if world.room_of(world.start_position) == room:
            tags.append((tr("tag.entrance"), t["text2"], t["fill2"]))
        if self._exit_visible(gm) and world.room_of(world.exit_position) == room:
            tags.append((tr("tag.exit"), t["success"], t["success_light"]))
        if room != agent_room:
            tags.append((tr("tag.preview"), t["primary"], t["primary_light"]))
        left = of.right + 14
        for text, fg, bg in tags:
            left = p.tag(text, (left, y0), fg, bg, anchor="midleft").right + 8

        for cell in world.room_cells(room):
            lr, lc = world.local(cell)
            rect = pygame.Rect(self.board_rect.x + lc * self.CELL, self.board_rect.y + lr * self.CELL, self.CELL, self.CELL)
            self._draw_cell(gm, cell, rect.inflate(-4, -4))

        # Traversed doors keep their destination labels even with Reveal map off.
        for a, b in world.doors:
            for here, there in ((a, b), (b, a)):
                if world.room_of(here) != room:
                    continue
                if not self.reveal_all and here not in gm.known_doors:
                    continue
                lr, lc = world.local(here)
                dr, dc = there[0] - here[0], there[1] - here[1]
                cx = self.board_rect.x + lc * self.CELL + self.CELL // 2
                cy = self.board_rect.y + lr * self.CELL + self.CELL // 2
                half = self.CELL // 2
                ex, ey = cx + dc * half, cy + dr * half
                label = f"R{world.room_of(there) + 1}"
                pill_c = (ex + dc * 24, ey + dr * 14)
                p.tag(label, pill_c, t["on_primary"], t["primary"], size=11, anchor="center", height=18)

        self._draw_arrow_flight(gm, room)

    BANNER_IN_MS, BANNER_HOLD_MS, BANNER_OUT_MS = 150, 900, 450

    def _draw_room_banner(self, gm, room):
        """Big room number over the board for a moment after entering a room."""
        if self._banner_room != room or gm.game_over:
            return
        elapsed = pygame.time.get_ticks() - self._banner_t0
        fade_out_at = self.BANNER_IN_MS + self.BANNER_HOLD_MS
        if elapsed > fade_out_at + self.BANNER_OUT_MS:
            self._banner_room = None
            return
        if elapsed < self.BANNER_IN_MS:
            alpha = elapsed / self.BANNER_IN_MS
        elif elapsed > fade_out_at:
            alpha = 1 - (elapsed - fade_out_at) / self.BANNER_OUT_MS
        else:
            alpha = 1.0

        # Draw onto a transparent layer so the whole banner fades together
        p, t = self.p, self.p.theme
        screen = p.screen
        layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        p.screen = layer
        try:
            box = pygame.Rect(0, 0, 200, 72)
            box.center = (self.board_rect.centerx, self.board_rect.centery - round(8 * (1 - alpha)))
            p.box(box.move(0, 4), t["border"], radius=12)
            p.box(box, t["card"], radius=12, border=t["border"])
            p.text(tr("room.title", n=room + 1), box.center, 28, t["text1"], "bold", anchor="center")
        finally:
            p.screen = screen
        layer.set_alpha(round(255 * max(0.0, min(1.0, alpha))))
        screen.blit(layer, (0, 0))

    ARROW_MS_PER_CELL = 90
    ARROW_HOLD_MS = 350  # arrow stays stuck in the wall / Wumpus, fading out

    def _draw_arrow_flight(self, gm, room):
        shot = gm.last_shot
        if shot is None:
            return
        now = pygame.time.get_ticks()
        if shot["id"] != self._shot_seen:
            self._shot_seen = shot["id"]
            self._shot_t0 = now
        world = gm.world
        if world.room_of(shot["start"]) != room:
            return

        def center(cell):
            lr, lc = world.local(cell)
            return (self.board_rect.x + lc * self.CELL + self.CELL // 2,
                    self.board_rect.y + lr * self.CELL + self.CELL // 2)

        direction = shot["direction"]
        dr, dc = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}[direction]
        (sx, sy), (ex, ey) = center(shot["start"]), center(shot["end"])
        if not shot["hit"]:  # a miss flies on until it hits the room wall
            edge = self.CELL // 2 - 14
            ex, ey = ex + dc * edge, ey + dr * edge
        cells = max(abs(shot["end"][0] - shot["start"][0]), abs(shot["end"][1] - shot["start"][1]))
        flight = max(1, cells) * self.ARROW_MS_PER_CELL
        elapsed = now - self._shot_t0
        if elapsed > flight + self.ARROW_HOLD_MS:
            return

        img = self.assets.get(f"arrow_{direction}")
        if img is None:
            return
        k = min(1.0, elapsed / flight)
        k = 1 - (1 - k) ** 2  # ease-out
        pos = (round(sx + (ex - sx) * k), round(sy + (ey - sy) * k))
        if elapsed > flight:
            img = img.copy()
            img.set_alpha(round(255 * (1 - (elapsed - flight) / self.ARROW_HOLD_MS)))
        # The tip leads: anchor the sprite so its head is at `pos`
        anchor = {"RIGHT": "midright", "LEFT": "midleft", "UP": "midtop", "DOWN": "midbottom"}[direction]
        self.p.blit(img, **{anchor: pos})

    def _draw_cell(self, gm, cell, rect):
        p, t = self.p, self.p.theme
        world, agent = gm.world, gm.agent
        kb = agent.knowledge
        visible = cell in agent.visited or self.reveal_all

        if not visible:
            safe = cell in kb["safe_cells"]
            if safe:
                p.box(rect, t["success_light"], radius=6, border=t["success"])
                p.tag(tr("cell.safe"), (rect.x + 6, rect.y + 6), t["on_primary"], t["success"], size=10, height=18,
                      weight="bold")
            else:
                p.box(rect, t["fog"], radius=6)
                p.text("?", rect.center, 24, t["fog_text"], "medium", anchor="center")
                if cell in kb["confirmed_pits"]:
                    p.tag(tr("cell.pit"), (rect.x + 6, rect.y + 6), t["danger"], t["danger_light"], size=11, height=20)
                elif cell == kb["confirmed_wumpus"]:
                    p.tag(tr("cell.wumpus"), (rect.x + 6, rect.y + 6), t["danger"], t["danger_light"], size=11, height=20)
            self._draw_markers(gm, cell, rect)  # doors stay hidden under fog; R-labels show the way
            return

        if cell in world.pits and self.assets.get("pit"):
            p.blit(self.assets["pit"], topleft=rect.topleft)
        elif self.assets.get("floor"):
            p.blit(self.assets["floor"], topleft=rect.topleft)
        else:
            p.box(rect, t["fill3"], radius=6)

        if cell == world.exit_position:
            self._blit("door", midbottom=(rect.centerx, rect.bottom - 6))
        self._draw_room_doors(world, cell, rect)

        if cell == world.wumpus and cell not in world.pits:
            img = self.assets.get("wumpus")
            if img and not world.is_wumpus_alive:
                faded = img.copy()
                faded.set_alpha(110)
                p.blit(faded, center=rect.center)
                self._blit("scream", center=rect.center)
            else:
                self._blit("wumpus", center=rect.center)

        if cell == world.gold and not world.gold_taken:
            self._blit("gold", center=rect.center)
            self._blit("glitter", center=rect.center)

        self._draw_percepts(world, cell, rect)

        if cell == agent.position:
            self._blit("hero", center=rect.center)

        self._draw_markers(gm, cell, rect)

    def _draw_percepts(self, world, cell, rect):
        """
        Each percept icon sits against the edge of the cell that faces its source:
        breeze towards each neighbouring pit, stench towards the Wumpus. A cell next to
        two pits shows two breeze icons. Drawn from the map itself so it also works in
        reveal mode; nothing on top of a pit or the Wumpus. Glitter is not drawn: it only
        exists on the gold cell itself and is used by the agent as a percept.
        """
        if cell in world.pits or cell == world.wumpus:
            return
        pad = 6
        for nb in world.get_adjacent(cell):
            if nb in world.pits:
                key = "breeze"
            elif nb == world.wumpus and world.is_wumpus_alive:
                key = "stench"
            else:
                continue
            dr, dc = nb[0] - cell[0], nb[1] - cell[1]
            if dr < 0:
                self._blit(key, midtop=(rect.centerx, rect.y + pad))
            elif dr > 0:
                self._blit(key, midbottom=(rect.centerx, rect.bottom - pad))
            elif dc < 0:
                self._blit(key, midleft=(rect.x + pad, rect.centery))
            else:
                self._blit(key, midright=(rect.right - pad, rect.centery))

    def _draw_room_doors(self, world, cell, rect):
        """Door sprite in the middle of a cell that leads into a neighbouring room."""
        if cell in world.door_cells:
            self._blit("door_small", center=rect.center)

    def _exit_visible(self, gm):
        return self.reveal_all or gm.agent.exit_pos is not None

    def _draw_markers(self, gm, cell, rect):
        p, t = self.p, self.p.theme
        world = gm.world
        if cell == world.start_position:
            p.tag(tr("cell.entrance"), (rect.x + 6, rect.bottom - 6), t["text2"], t["card"], size=10, anchor="bottomleft",
                  height=18, weight="bold")
        if cell == world.exit_position and self._exit_visible(gm):
            p.tag(tr("cell.exit"), (rect.x + 6, rect.bottom - 6), t["on_primary"], t["success"], size=10, anchor="bottomleft",
                  height=18, weight="bold")

    # ------------------------------------------------------------------
    # Minimap
    # ------------------------------------------------------------------
    def _draw_minimap(self, gm, view_room):
        p, t = self.p, self.p.theme
        world, agent = gm.world, gm.agent
        r = self.map_rect
        p.text(tr("map.title"), (r.x + 20, r.y + 28), 16, t["text1"], "bold", anchor="midleft")
        explored = len(agent.visited)
        p.text(tr("map.explored", a=explored, b=len(world.cells)), (r.right - 20, r.y + 28), 13, t["text3"],
               anchor="midright")

        area = pygame.Rect(r.x + 20, r.y + 56, r.width - 40, r.height - 72)
        S = world.room_size
        gap = 18
        cols, rows = world.room_cols, world.room_rows
        cp = min((area.width - (cols - 1) * gap) / (cols * S), (area.height - (rows - 1) * gap) / (rows * S), 16)
        cp = max(4, int(cp))
        room_px = cp * S
        total_w = cols * room_px + (cols - 1) * gap
        total_h = rows * room_px + (rows - 1) * gap
        ox = area.x + (area.width - total_w) // 2
        oy = area.y + (area.height - total_h) // 2

        def cell_rect(cell):
            ry, rx = cell[0] // S, cell[1] // S
            lr, lc = cell[0] % S, cell[1] % S
            return pygame.Rect(ox + rx * (room_px + gap) + lc * cp, oy + ry * (room_px + gap) + lr * cp, cp, cp)

        # Door connectors
        for a, b in world.doors:
            ra, rb = cell_rect(a), cell_rect(b)
            line = ra.union(rb).inflate(-cp // 2, -cp // 2) if cp > 6 else ra.union(rb)
            p.box(line, t["fill4"], radius=2)

        self._minimap_rooms = []
        kb = agent.knowledge
        for idx, (ry, rx) in enumerate(world.rooms):
            room_rect = pygame.Rect(ox + rx * (room_px + gap), oy + ry * (room_px + gap), room_px, room_px)
            self._minimap_rooms.append((room_rect.inflate(6, 6), idx))
            for cell in world.room_cells(idx):
                cr = cell_rect(cell).inflate(-1, -1)
                if cell in agent.visited:
                    color = t["primary_light2"]
                elif cell in kb["safe_cells"]:
                    color = t["success_light"]
                else:
                    color = t["fill2"]
                p.box(cr, color, radius=2)
                dot = max(2, cp // 4)
                if cell in kb["confirmed_pits"] or cell == kb["confirmed_wumpus"]:
                    p.box(cr, None, radius=2, border=t["danger"])
                if self.reveal_all or cell in agent.visited:
                    if cell in world.pits:
                        p.circle(cr.center, dot + 1, t["text2"])
                    elif cell == world.wumpus:
                        p.circle(cr.center, dot + 1, t["danger"] if world.is_wumpus_alive else t["text4"])
                    elif cell == world.gold and not world.gold_taken:
                        p.circle(cr.center, dot + 1, t["gold"])
                if cell == world.exit_position and self._exit_visible(gm):
                    p.box(cr.inflate(-2, -2), t["success"], radius=2)
                elif cell == world.start_position:
                    p.box(cr.inflate(-2, -2), None, radius=2, border=t["text3"], border_width=2)
            border = t["primary"] if idx == view_room else t["border"]
            p.box(room_rect.inflate(4, 4), None, radius=4, border=border, border_width=2 if idx == view_room else 1)
            p.text(f"R{idx + 1}", (room_rect.x, room_rect.y - 4), 10, t["text3"], "medium", anchor="bottomleft")

        ar = cell_rect(agent.position)
        p.circle(ar.center, max(3, cp // 2 - 1) + 1, t["card"])
        p.circle(ar.center, max(3, cp // 2 - 1), t["primary"])

    # ------------------------------------------------------------------
    # Agent panel
    # ------------------------------------------------------------------
    def _status(self, gm):
        t = self.p.theme
        if gm.victory:
            return tr("status.victory"), t["success"], t["success_light"]
        if gm.death_reason == "TRAPPED":
            return tr("status.trapped"), t["warning"], t["warning_light"]
        if gm.death_reason:
            return tr("status.dead"), t["danger"], t["danger_light"]
        if gm.agent.escaped:
            return tr("status.escaped"), t["warning"], t["warning_light"]
        if gm.auto_mode:
            return tr("status.auto"), t["primary"], t["primary_light"]
        if gm.play_mode == "manual":
            return tr("status.manual"), t["primary"], t["primary_light"]
        return tr("status.waiting"), t["text2"], t["fill2"]

    def _draw_info(self, gm):
        p, t = self.p, self.p.theme
        agent = gm.agent
        r = self.info_rect
        x, w = r.x + 20, r.width - 40

        p.text(tr("agent.title"), (x, r.y + 28), 16, t["text1"], "bold", anchor="midleft")
        status, fg, bg = self._status(gm)
        p.tag(status, (r.right - 20, r.y + 28), fg, bg, anchor="midright")

        # Statistics
        y = r.y + 54
        stats = [
            (tr("stat.score"), str(gm.score), t["text1"]),
            (tr("stat.steps"), str(gm.steps), t["text1"]),
            (tr("stat.gold"), tr("gold.found") if agent.has_gold else tr("gold.not_yet"),
             t["gold"] if agent.has_gold else t["text3"]),
            (tr("stat.arrow"), "1" if agent.has_arrow else "0", t["text1"] if agent.has_arrow else t["text3"]),
        ]
        col = w / len(stats)
        for i, (label, value, color) in enumerate(stats):
            sx = x + i * col
            p.text(label, (sx, y), 12, t["text3"])
            p.text(value, (sx, y + 18), 20, color, "bold")

        y += 56
        p.line((x, y), (x + w, y), t["border"])

        # Percepts at the current cell
        y += 14
        label = p.text(tr("label.percepts"), (x, y + 11), 12, t["text3"], anchor="midleft")
        percepts = agent.percepts_history.get(agent.position, set())
        tx = max(x + 70, label.right + 12)
        palette = {
            "breeze": (t["cyan"], t["cyan_light"]),
            "stench": (t["success"], t["success_light"]),
            "glitter": (t["gold"], t["gold_light"]),
            "scream": (t["danger"], t["danger_light"]),
        }
        for name, (fg, bg) in palette.items():
            on = name in percepts
            tag = p.tag(tr(f"percept.{name}"), (tx, y), fg if on else t["text4"], bg if on else t["fill1"])
            tx = tag.right + 8

        # Reasoning
        y += 36
        p.text(tr("label.reasoning"), (x, y), 12, t["text3"])
        y += 20
        for line in p.wrap(agent.thought_process, w, 13)[:3]:
            p.text(line, (x, y), 13, t["text1"])
            y += 19

        # Event log
        y += 8
        p.text(tr("label.log"), (x, y), 12, t["text3"])
        y += 20
        room_for = max(0, (r.bottom - 14 - y) // 18)
        for line in gm.logs[-room_for:] if room_for else []:
            line = str(line)
            text = line if p.text_width(line, 12) <= w else line[: max(0, int(len(line) * w / p.text_width(line, 12)) - 1)] + "..."
            p.text(text, (x, y), 12, t["text2"])
            y += 18

    # ------------------------------------------------------------------
    # Result overlay
    # ------------------------------------------------------------------
    def _draw_result(self, gm):
        p, t = self.p, self.p.theme
        p.alpha_box(self.board_rect.inflate(8, 8), t["overlay"], radius=8)

        if gm.victory:
            title, desc, color = tr("result.victory.title"), tr("result.victory.desc"), t["success"]
        elif gm.death_reason == "FALL_IN_PIT":
            title, desc, color = tr("result.pit.title"), tr("result.learn"), t["danger"]
        elif gm.death_reason == "EATEN_BY_WUMPUS":
            title, desc, color = tr("result.wumpus.title"), tr("result.learn"), t["danger"]
        elif gm.death_reason == "TRAPPED":
            title, desc, color = tr("result.trapped.title"), tr("result.trapped.desc"), t["warning"]
        else:
            title, desc, color = tr("result.escaped.title"), tr("result.escaped.desc"), t["warning"]

        modal = pygame.Rect(0, 0, 360, 168)
        modal.center = self.board_rect.center
        p.box(modal.move(0, 4), t["border"], radius=8)
        p.box(modal, t["card"], radius=8, border=t["border"])
        p.circle((modal.x + 36, modal.y + 40), 10, color)
        p.text(title, (modal.x + 56, modal.y + 40), 18, t["text1"], "bold", anchor="midleft")
        p.text(desc, (modal.x + 24, modal.y + 76), 14, t["text2"])
        p.text(tr("result.final"), (modal.x + 24, modal.y + 112), 12, t["text3"])
        p.text(str(gm.score), (modal.x + 24, modal.y + 128), 20, t["text1"], "bold")
        p.text(tr("result.hint"), (modal.right - 24, modal.y + 140), 12, t["text3"], anchor="midright")
