"""
Explanation board: a free-form Wumpus World map for demos and lectures.

Left: a grid of cells. Right: a palette of icons.
- Drag an icon from the palette onto a cell to place it (the palette never runs out).
- Drag a placed icon to move it; drop it outside the map to remove it.
- Right-click an icon on the map to remove it.
- Cells are drawn like the game: same sprite sizes and layers. Breeze and stench
  are pulled to the edge that faces a neighbouring pit / Wumpus, as in the game.
- Keys: + / - grid size, C clear, T dark theme, Esc quit.

Run: python board.py
"""
import itertools

import pygame

from ui.painter import Painter
from ui.paths import asset
from ui.theme import LIGHT, DARK

WINDOW_SIZE = (1200, 800)
MIN_SIZE, MAX_SIZE = 3, 8
GAME_CELL = 124  # cell size in the main game; sprite sizes below are relative to it

# (key, label, image file)
ICONS = [
    ("hero", "Agent", "hero.png"),
    ("wumpus", "Wumpus", "wumpus.png"),
    ("pit", "Pit", "pit.png"),
    ("gold", "Gold", "gold.png"),
    ("breeze", "Breeze", "breeze.png"),
    ("stench", "Stench", "scream.png"),
    ("glitter", "Glitter", "giltter.png"),
    ("door", "Door", "door.png"),
    ("arrow", "Arrow", "arrow.png"),
]
OBJECTS = {"hero", "wumpus", "pit", "gold", "door"}  # at most one of each per cell
PERCEPTS = {"breeze": "pit", "stench": "wumpus"}  # percept -> the thing it points to
SMALL = {"breeze", "stench", "glitter"}
# Draw order, bottom to top (same as the game: door, wumpus, gold, percepts, hero)
LAYER = {"pit": 0, "door": 1, "wumpus": 2, "gold": 3, "glitter": 4, "breeze": 5, "stench": 5, "arrow": 6, "hero": 7}
DIRS = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


class Sprites:
    """Loads each image once and keeps scaled copies per size."""

    def __init__(self, painter):
        self.p = painter
        self.raw, self.cropped = {}, {}
        self._cache = {}
        for key, _, file in ICONS + [("floor", "", "floor.png")]:
            try:
                img = pygame.image.load(asset(file))
                self.raw[key] = img
                self.cropped[key] = img.subsurface(img.get_bounding_rect(min_alpha=10)).copy()
            except (pygame.error, FileNotFoundError, ValueError) as e:
                print(f"Error loading {file}: {e}")
                self.raw[key] = self.cropped[key] = None

    def _scaled(self, kind, key, size):
        size = (round(size[0]), round(size[1]))
        img = (self.raw if kind == "raw" else self.cropped).get(key)
        if img is None:
            return None
        if (kind, key, size) not in self._cache:
            self._cache[(kind, key, size)] = self.p.scale_image(img, size)
        return self._cache[(kind, key, size)]

    def fit(self, key, w, h):
        """Cropped icon fitted into a w x h box, keeping its proportions."""
        img = self.cropped.get(key)
        if img is None:
            return None
        iw, ih = img.get_size()
        f = min(w / iw, h / ih)
        return self._scaled("crop", key, (iw * f, ih * f))

    def cell_sprite(self, key, cell):
        """Sprite at the same size as the game draws it in a cell of `cell` px."""
        c = cell
        if key in ("floor", "pit"):
            return self._scaled("raw", key, (c - 4, c - 4))
        if key in ("hero", "wumpus"):
            return self._scaled("raw", key, (c * 0.78, c * 0.78))
        if key == "gold":
            return self._scaled("raw", key, (c * 0.6, c * 0.6))
        if key == "door":
            return self._scaled("raw", key, (c * 0.44, c * 0.58))
        if key in SMALL:
            hint = 30 * c / GAME_CELL  # the game's percept box
            return self.fit(key, hint * 1.3, hint)
        if key == "arrow":
            return self.fit(key, c * 0.45, c * 0.45)
        return None


class Board:
    def __init__(self, screen):
        self.p = Painter(screen, WINDOW_SIZE[0])
        self.sprites = Sprites(self.p)
        self.size = 4
        self.cells = {}  # (row, col) -> list of {"key", "id"}
        self.drag = None  # {"item": {...}}
        self.mouse = (0, 0)
        self.pos = {}  # item id -> current drawn center (moves smoothly toward its target)
        self._ids = itertools.count()

        self.map_card = pygame.Rect(20, 20, 820, 760)
        self.side_card = pygame.Rect(856, 20, 324, 760)
        self.palette = self._layout_palette()
        self.buttons = self._layout_buttons()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    @property
    def grid_rect(self):
        area = 660
        cell = area // self.size
        side = cell * self.size
        x = self.map_card.x + (self.map_card.width - side) // 2
        y = self.map_card.y + 72 + (area - side) // 2
        return pygame.Rect(x, y, side, side)

    @property
    def cell_size(self):
        return self.grid_rect.width // self.size

    def _layout_palette(self):
        slots = []
        x0, y0 = self.side_card.x + 20, self.side_card.y + 72
        w, h, gap = 88, 104, 10
        for i, (key, label, _) in enumerate(ICONS):
            r, c = divmod(i, 3)
            slots.append((pygame.Rect(x0 + c * (w + gap), y0 + r * (h + gap), w, h), key, label))
        return slots

    def _layout_buttons(self):
        x, y = self.side_card.x + 20, self.side_card.bottom - 60
        return [
            (pygame.Rect(x, y, 40, 40), "minus"),
            (pygame.Rect(x + 48, y, 40, 40), "plus"),
            (pygame.Rect(x + 100, y, 88, 40), "clear"),
            (pygame.Rect(x + 196, y, 88, 40), "theme"),
        ]

    def cell_at(self, pos):
        g = self.grid_rect
        if not g.collidepoint(pos):
            return None
        return ((pos[1] - g.y) // self.cell_size, (pos[0] - g.x) // self.cell_size)

    def cell_rect(self, row, col):
        """Tile area of a cell (2 px gap on each side, like the game board)."""
        g, c = self.grid_rect, self.cell_size
        return pygame.Rect(g.x + col * c + 2, g.y + row * c + 2, c - 4, c - 4)

    def has(self, cell, key):
        return any(it["key"] == key for it in self.cells.get(cell, []))

    def _source_dirs(self, cell, source):
        """Directions (UP/DOWN/LEFT/RIGHT) of neighbouring cells that hold `source`."""
        r, c = cell
        return [d for d, (dr, dc) in DIRS.items() if self.has((r + dr, c + dc), source)]

    def layout(self, cell):
        """
        Where each item of a cell sits: list of (item, anchor, point, sprite), bottom layer first.
        Breeze / stench go to the edge facing their source; extra ones take the free edges.
        """
        rect = self.cell_rect(*cell)
        cs = self.cell_size
        pad = round(6 * cs / GAME_CELL)
        edges = {
            "UP": ("midtop", (rect.centerx, rect.y + pad)),
            "DOWN": ("midbottom", (rect.centerx, rect.bottom - pad)),
            "LEFT": ("midleft", (rect.x + pad, rect.centery)),
            "RIGHT": ("midright", (rect.right - pad, rect.centery)),
        }
        items = sorted(self.cells.get(cell, []), key=lambda it: LAYER[it["key"]])

        # Pick an edge for every breeze / stench
        used, wanted = set(), {}
        for key, source in PERCEPTS.items():
            dirs = self._source_dirs(cell, source)
            for it in (i for i in items if i["key"] == key):
                d = next((d for d in dirs if d not in used), None)
                if d:
                    wanted[it["id"]] = d
                    used.add(d)
        for it in items:
            if it["key"] in PERCEPTS and it["id"] not in wanted:
                d = next((d for d in ("UP", "RIGHT", "DOWN", "LEFT") if d not in used), "UP")
                wanted[it["id"]] = d
                used.add(d)

        out = []
        for it in items:
            key = it["key"]
            sprite = self.sprites.cell_sprite(key, cs)
            if key == "pit":
                out.append((it, "topleft", rect.topleft, sprite))
            elif key == "door":
                out.append((it, "midbottom", (rect.centerx, rect.bottom - pad), sprite))
            elif key in PERCEPTS:
                anchor, point = edges[wanted[it["id"]]]
                out.append((it, anchor, point, sprite))
            elif key == "glitter":  # sits next to the gold, in the lower right corner
                out.append((it, "bottomright", (rect.right - pad, rect.bottom - pad), sprite))
            else:
                out.append((it, "center", rect.center, sprite))
        return out

    @staticmethod
    def _sprite_rect(sprite, anchor, point, k):
        w, h = (sprite.get_width() / k, sprite.get_height() / k) if sprite else (30, 30)
        r = pygame.Rect(0, 0, round(w), round(h))
        setattr(r, anchor, point)
        return r

    def item_at(self, pos):
        """Topmost item under the mouse: (cell, item)."""
        cell = self.cell_at(pos)
        if cell is None:
            return None
        hits = []
        for it, anchor, point, sprite in self.layout(cell):
            if it["key"] == "pit":
                continue  # the pit tile is picked only if nothing else is under the mouse
            if self._sprite_rect(sprite, anchor, point, self.p.k).collidepoint(pos):
                hits.append(it)
        if not hits:
            hits = [it for it in self.cells.get(cell, []) if it["key"] == "pit"]
        return (cell, hits[-1]) if hits else None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def resize(self, delta):
        self.size = max(MIN_SIZE, min(MAX_SIZE, self.size + delta))
        self.cells = {k: v for k, v in self.cells.items() if k[0] < self.size and k[1] < self.size}
        self.pos.clear()

    def place(self, item, cell):
        items = self.cells.setdefault(cell, [])
        key = item["key"]
        limit = 1 if key in OBJECTS else 4 if key in PERCEPTS else 1
        if sum(it["key"] == key for it in items) < limit:
            items.append(item)
        if not items:
            del self.cells[cell]

    def take(self, cell, item):
        self.cells[cell].remove(item)
        if not self.cells[cell]:
            del self.cells[cell]
        return item

    def press_button(self, name):
        if name == "minus":
            self.resize(-1)
        elif name == "plus":
            self.resize(1)
        elif name == "clear":
            self.cells.clear()
            self.pos.clear()
        elif name == "theme":
            self.p.theme = LIGHT if self.p.theme is DARK else DARK

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, key, _ in self.palette:
                if rect.collidepoint(event.pos):
                    self.drag = {"item": {"key": key, "id": next(self._ids)}}
                    return
            hit = self.item_at(event.pos)
            if hit:
                self.drag = {"item": self.take(*hit)}
                return
            for rect, name in self.buttons:
                if rect.collidepoint(event.pos):
                    self.press_button(name)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag:
            item = self.drag["item"]
            cell = self.cell_at(event.pos)
            if cell is not None:
                self.pos[item["id"]] = event.pos  # starts where it was dropped, then slides into place
                self.place(item, cell)
            self.drag = None  # dropped outside the map: icon is removed
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            hit = self.item_at(event.pos)
            if hit:
                self.take(*hit)
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                self.resize(1)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.resize(-1)
            elif event.key == pygame.K_c:
                self.press_button("clear")
            elif event.key == pygame.K_t:
                self.press_button("theme")

    def cursor(self):
        if self.drag:
            return pygame.SYSTEM_CURSOR_SIZEALL
        pos = self.mouse
        clickable = (
            any(r.collidepoint(pos) for r, _, _ in self.palette)
            or any(r.collidepoint(pos) for r, _ in self.buttons)
            or self.item_at(pos) is not None
        )
        return pygame.SYSTEM_CURSOR_HAND if clickable else pygame.SYSTEM_CURSOR_ARROW

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self):
        p, t = self.p, self.p.theme
        p.screen.fill(t["bg"])
        self._draw_map()
        self._draw_side()
        if self.drag:
            sprite = self.sprites.cell_sprite(self.drag["item"]["key"], self.cell_size)
            p.blit(sprite, center=self.mouse)

    def _draw_item(self, item, anchor, point, sprite):
        """Draws an item, easing it from where it was dropped toward its spot in the cell."""
        target = self._sprite_rect(sprite, anchor, point, self.p.k).center
        cur = self.pos.get(item["id"], target)
        nxt = (cur[0] + (target[0] - cur[0]) * 0.2, cur[1] + (target[1] - cur[1]) * 0.2)
        if abs(nxt[0] - target[0]) < 0.5 and abs(nxt[1] - target[1]) < 0.5:
            nxt = target
        self.pos[item["id"]] = nxt
        self.p.blit(sprite, center=(round(nxt[0]), round(nxt[1])))

    def _draw_map(self):
        p, t = self.p, self.p.theme
        card = self.map_card
        p.box(card, t["card"], radius=8, border=t["border"])
        p.text("Map", (card.x + 24, card.y + 22), 20, weight="bold")
        p.text(f"{self.size} x {self.size}", (card.right - 24, card.y + 26), 14, t["text3"], anchor="topright")

        hover = self.cell_at(self.mouse) if self.drag else None
        floor = self.sprites.cell_sprite("floor", self.cell_size)
        for row in range(self.size):
            for col in range(self.size):
                rect = self.cell_rect(row, col)
                if self.has((row, col), "pit"):
                    pass  # the pit sprite is a full tile with its own floor
                elif floor is not None:
                    p.blit(floor, topleft=rect.topleft)
                else:
                    p.box(rect, t["fill3"], radius=6)
                for item, anchor, point, sprite in self.layout((row, col)):
                    if item["key"] == "pit":
                        p.blit(sprite, topleft=rect.topleft)
                    else:
                        self._draw_item(item, anchor, point, sprite)
                if hover == (row, col):
                    p.alpha_box(rect, (*t["primary"], 70), radius=4)
                    p.box(rect, None, radius=4, border=t["primary"], border_width=2)

        # Coordinates: row numbers on the left, column numbers on top (1-based, like the game)
        g, c = self.grid_rect, self.cell_size
        for i in range(self.size):
            p.text(str(i + 1), (g.x - 12, g.y + i * c + c // 2), 13, t["text3"], anchor="center")
            p.text(str(i + 1), (g.x + i * c + c // 2, g.y - 14), 13, t["text3"], anchor="center")

    def _draw_side(self):
        p, t = self.p, self.p.theme
        card = self.side_card
        p.box(card, t["card"], radius=8, border=t["border"])
        p.text("Icons", (card.x + 24, card.y + 22), 20, weight="bold")

        for rect, key, label in self.palette:
            hovered = rect.collidepoint(self.mouse) and not self.drag
            p.box(rect, t["primary_light"] if hovered else t["fill1"], radius=6,
                  border=t["primary"] if hovered else t["border"])
            box = 34 if key in SMALL else 52
            p.blit(self.sprites.fit(key, box, box), center=(rect.centerx, rect.y + 42))
            p.text(label, (rect.centerx, rect.bottom - 16), 13, t["text2"], weight="medium", anchor="center")

        tips = [
            "Drag an icon onto a cell",
            "Drag a placed icon to move it",
            "Drop outside the map to remove",
            "Right-click an icon to remove",
            "Breeze / stench stick to the side",
            "    facing a pit / the Wumpus",
        ]
        y = self.palette[-1][0].bottom + 24
        p.text("How to use", (card.x + 24, y), 14, weight="bold")
        for i, tip in enumerate(tips):
            if tip.startswith(" "):  # continuation line, aligned with the text above
                p.text(tip.strip(), (card.x + 24 + p.text_width("•  ", 13), y + 28 + i * 24), 13, t["text2"])
            else:
                p.text(f"•  {tip}", (card.x + 24, y + 28 + i * 24), 13, t["text2"])

        p.text("Grid size  ·  Clear (C)  ·  Theme (T)", (card.x + 24, card.bottom - 86), 12, t["text3"])
        labels = {"minus": "−", "plus": "+", "clear": "Clear", "theme": "Light" if p.theme is DARK else "Dark"}
        for rect, name in self.buttons:
            hovered = rect.collidepoint(self.mouse)
            primary = name in ("minus", "plus")
            bg = t["primary_hover" if hovered else "primary"] if primary else t["fill3" if hovered else "fill2"]
            fg = t["on_primary"] if primary else t["text1"]
            p.box(rect, bg, radius=6)
            p.text(labels[name], rect.center, 18 if primary else 14, fg, weight="medium", anchor="center")


def create_window(title):
    """Sharp window on Retina screens with pygame-ce; regular window otherwise."""
    if hasattr(pygame, "Window"):
        window = pygame.Window(title, WINDOW_SIZE, allow_high_dpi=True)
        return window.get_surface(), window.flip
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption(title)
    return screen, pygame.display.flip


def main():
    pygame.init()
    screen, show_frame = create_window("Wumpus World - Explanation Board")
    clock = pygame.time.Clock()
    board = Board(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            else:
                board.handle(event)
        pygame.mouse.set_cursor(board.cursor())
        board.draw()
        show_frame()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
