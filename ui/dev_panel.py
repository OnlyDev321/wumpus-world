"""
Dev mode: a draggable Analytics window with live stats, session totals and a benchmark
that compares algorithms on the same maps.
"""
import pygame

from game.algorithms import ALGORITHMS
from game.benchmark import Benchmark
from game.i18n import T, tr, algorithm_label
from ui.widgets import Button, Segmented


class DevPanel:
    W, H = 480, 690
    HEADER = 52

    def __init__(self, gm, window_size):
        self.gm = gm
        self.window = pygame.Rect((0, 0), window_size)
        self.rect = pygame.Rect(window_size[0] - self.W - 40, 40, self.W, self.H)
        self.open = False
        self.dragging = False
        self._grab_offset = (0, 0)
        self.bench_games = 100
        self.benchmark = None
        self.bench_results = {}  # (algorithm, rooms, games) -> summary

        names = list(ALGORITHMS)
        running = lambda: self.benchmark is not None
        # (widget, position relative to the window's top-left)
        self._widgets = [
            (Button((0, 0, 28, 28), "x", self.toggle), (self.W - 44, 12)),
            (Segmented((0, 0, self.W - 40, 32), [(n, algorithm_label(n)) for n in names],
                       lambda: self.gm.algorithm, self._set_algorithm), (20, 84)),
            (Segmented((0, 0, 170, 32), [(50, "50"), (100, "100"), (250, "250")],
                       lambda: self.bench_games, self._set_games), (20, 0)),
            (Button((0, 0, 150, 32), T("dev.run"), self._run, kind="primary",
                    enabled=lambda: not running()), (self.W - 170, 0)),
            (Button((0, 0, 64, 22), T("dev.clear"), self._clear_session), (self.W - 84, 0)),
        ]
        self._layout_y = {}

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def toggle(self):
        self.open = not self.open
        self.dragging = False

    def _set_algorithm(self, name):
        self.gm.set_algorithm(ALGORITHMS[name])

    def _set_games(self, n):
        self.bench_games = n

    def _run(self):
        self.benchmark = Benchmark(self.gm.algorithm, self.gm.num_rooms, self.bench_games)

    def _clear_session(self):
        self.gm.history.clear()

    def update(self):
        """Advances a running benchmark a little each frame."""
        if self.benchmark:
            self.benchmark.step(12)
            if self.benchmark.done:
                b = self.benchmark
                self.bench_results[(b.algo_name, b.rooms, b.games)] = b.summary()
                self.benchmark = None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def _sync(self):
        """Moves widgets with the window (some rows are placed while drawing)."""
        for i, (w, (rx, ry)) in enumerate(self._widgets):
            ry = self._layout_y.get(i, ry)
            w.rect.topleft = (self.rect.x + rx, self.rect.y + ry)

    def header_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.W, self.HEADER)

    def hovering_header(self, pos):
        return self.open and self.header_rect().collidepoint(pos) and not self._widgets[0][0].hit(pos)

    def handle(self, event):
        """Returns True when the event belongs to the window (it is then not passed on)."""
        if not self.open:
            return False
        self._sync()
        for w, _ in self._widgets:
            if w.handle(event):
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovering_header(event.pos):
            self.dragging = True
            self._grab_offset = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.rect.topleft = (event.pos[0] - self._grab_offset[0], event.pos[1] - self._grab_offset[1])
            self.rect.clamp_ip(self.window)
            return True
        if event.type == pygame.MOUSEBUTTONUP and self.dragging:
            self.dragging = False
            return True
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and self.rect.collidepoint(event.pos):
            return True
        return False

    def hovering_control(self, pos):
        return self.open and any(w.hit(pos) and w.enabled for w, _ in self._widgets)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _section(self, p, title, y):
        t = p.theme
        p.line((self.rect.x + 20, y), (self.rect.right - 20, y), t["border"])
        p.text(str(title).upper(), (self.rect.x + 20, y + 20), 11, t["text3"], "medium", anchor="midleft")
        return y + 34

    def _grid(self, p, items, y, cols=3):
        """Label/value statistics laid out in columns; returns the y below them."""
        t = p.theme
        col_w = (self.W - 40) / cols
        for i, (label, value, color) in enumerate(items):
            x = self.rect.x + 20 + (i % cols) * col_w
            row_y = y + (i // cols) * 44
            p.text(label, (x, row_y), 12, t["text3"])
            p.text(value, (x, row_y + 17), 15, color or t["text1"], "medium")
        return y + ((len(items) + cols - 1) // cols) * 44

    def draw(self, p):
        if not self.open:
            return
        t = p.theme
        gm = self.gm
        r = self.rect

        # Shadow, body and header
        for spread, alpha in ((14, 10), (8, 14), (3, 18)):  # soft layered shadow
            p.alpha_box(r.move(0, 4).inflate(spread, spread), (0, 0, 0, alpha), radius=8 + spread // 2)
        p.box(r, t["card"], radius=8, border=t["border"])
        p.text(tr("dev.title"), (r.x + 20, r.y + 22), 16, t["text1"], "bold", anchor="midleft")
        p.text(tr("dev.subtitle"), (r.x + 20, r.y + 40), 11, t["text3"], anchor="midleft")
        p.text(tr("dev.algorithm").upper(), (r.x + 20, r.y + 70), 11, t["text3"], "medium", anchor="midleft")

        # Current game
        res = gm.result()
        outcome = res["outcome"]
        outcome_color = {"win": t["success"], "pit": t["danger"], "wumpus": t["danger"]}.get(
            outcome, t["warning"] if outcome else t["text1"])
        y = self._section(p, tr("dev.current"), r.y + 132)
        y = self._grid(p, [
            (tr("dev.outcome"), tr(f"outcome.{outcome or 'none'}"), outcome_color),
            (tr("stat.steps"), str(res["steps"]), None),
            (tr("dev.explored"), f"{len(gm.agent.visited)}/{len(gm.world.cells)} ({res['explored']:.0%})", None),
            (tr("dev.think_avg"), f"{res['think_ms_avg']:.2f} ms", None),
            (tr("dev.think_max"), f"{res['think_ms_max']:.2f} ms", None),
            (tr("dev.risky"), str(res["risky"]), None),
            (tr("dev.doors"), str(res["doors"]), None),
            (tr("dev.slain"), tr("dev.slain_yes", bonus=gm.WUMPUS_BONUS) if res["kills"]
             else tr("dev.slain_missed") if res["shots"] else tr("dev.slain_no"),
             t["success"] if res["kills"] else None),
            (tr("dev.time"), f"{res['duration_s']:.1f} s", None),
        ], y)

        # Session
        y = self._section(p, tr("dev.session"), y + 6)
        self._layout_y[4] = y - 25 - r.y  # 'Clear' sits on the Session title row
        hist = gm.history
        n = len(hist)
        rate = lambda o: f"{sum(h['outcome'] == o for h in hist) / n:.0%}" if n else "-"
        avg = lambda k, fmt: format(sum(h[k] for h in hist) / n, fmt) if n else "-"
        y = self._grid(p, [
            (tr("dev.games"), str(n), None),
            (tr("dev.win_rate"), rate("win"), t["success"] if n else None),
            (tr("dev.avg_score"), avg("score", ".0f"), None),
            (tr("dev.deaths"), f"{rate('pit')} / {rate('wumpus')}" if n else "-", None),
            (tr("dev.avg_steps"), avg("steps", ".1f"), None),
            (tr("dev.avg_explored"), avg("explored", ".0%"), None),
            (tr("dev.kill_rate"), f"{sum(h['kills'] > 0 for h in hist) / n:.0%}" if n else "-", None),
        ], y)

        # Benchmark
        y = self._section(p, tr("dev.benchmark", n=gm.num_rooms), y + 6)
        self._layout_y[2] = y - r.y
        self._layout_y[3] = y - r.y
        y += 44
        if self.benchmark:
            bar = pygame.Rect(r.x + 20, y, self.W - 40, 6)
            p.box(bar, t["fill2"], radius=3)
            p.box(pygame.Rect(bar.x, bar.y, max(6, int(bar.width * self.benchmark.progress)), 6), t["primary"], radius=3)
            p.text(tr("dev.running", algo=algorithm_label(self.benchmark.algo_name), a=len(self.benchmark.results),
                      b=self.benchmark.games),
                   (bar.x, y + 16), 12, t["text2"])
            y += 44
        self._draw_table(p, y)
        self._sync()
        for w, _ in self._widgets:
            w.draw(p)

    def _draw_table(self, p, y):
        t = p.theme
        r = self.rect
        rows = [(name, self.bench_results.get((name, self.gm.num_rooms, self.bench_games))) for name in ALGORITHMS]
        cols = [(tr("col.algorithm"), 0), (tr("col.win"), 140), (tr("col.pit"), 185), (tr("col.kill"), 230),
                (tr("col.score"), 275), (tr("col.steps"), 330), (tr("col.ms"), 385)]
        for label, dx in cols:
            p.text(label, (r.x + 20 + dx, y), 11, t["text3"], "medium")
        y += 20
        for name, s in rows:
            p.line((r.x + 20, y), (r.right - 20, y), t["border"])
            current = name == self.gm.algorithm
            p.text(algorithm_label(name), (r.x + 20, y + 14), 13, t["primary"] if current else t["text1"],
                   "medium" if current else "regular", anchor="midleft")
            values = ["-"] * 6 if not s else [
                f"{s['win']:.0%}", f"{s['pit']:.0%}", f"{s['kills']:.0%}", f"{s['score']:.0f}", f"{s['steps']:.1f}",
                f"{s['think_ms']:.2f}"]
            for (_, dx), value in zip(cols[1:], values):
                p.text(value, (r.x + 20 + dx, y + 14), 13, t["text1"], anchor="midleft")
            y += 28
        if not any(s for _, s in rows):
            p.text(tr("dev.empty", n=self.bench_games), (r.x + 20, y + 8), 12, t["text3"])
