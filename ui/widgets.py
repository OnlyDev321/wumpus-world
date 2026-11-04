import pygame


class Widget:
    """Base clickable element. State is read through callbacks, so keyboard shortcuts stay in sync."""

    def __init__(self, rect, enabled=None):
        self.rect = pygame.Rect(rect)
        self._enabled = enabled or (lambda: True)
        self.hover = False
        self.pressed = False
        self.hotkey = None  # keyboard shortcut shown in a tooltip on hover

    @property
    def enabled(self):
        return self._enabled()

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def handle(self, event):
        """Returns True when the event was consumed by this widget."""
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.hit(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hit(event.pos):
            self.pressed = True
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed, self.pressed = self.pressed, False
            if was_pressed and self.hit(event.pos) and self.enabled:
                self.click(event.pos)
                return True
        return False

    def click(self, pos):
        pass

    def draw(self, p):
        pass


class Button(Widget):
    """kind: 'primary' (filled blue) or 'secondary' (grey fill)."""

    def __init__(self, rect, label, on_click, kind="secondary", enabled=None, icon=None):
        super().__init__(rect, enabled)
        self.label = label
        self.on_click = on_click
        self.kind = kind
        self.icon = icon  # 'UP' / 'DOWN' / 'LEFT' / 'RIGHT' draws an arrow instead of text

    def click(self, pos):
        self.on_click()

    def draw(self, p):
        t = p.theme
        active = self.hover and self.enabled
        if self.kind == "primary":
            if not self.enabled:
                bg, fg = t["primary_light2"], t["on_primary"]
            else:
                bg = t["primary_active"] if self.pressed else (t["primary_hover"] if active else t["primary"])
                fg = t["on_primary"]
        else:
            bg = t["fill4"] if self.pressed and active else (t["fill3"] if active else t["fill2"])
            fg = t["text1"] if self.enabled else t["text4"]
        p.box(self.rect, bg, radius=4)
        if self.icon:
            p.triangle(self.rect.center, 5, self.icon, fg)
        else:
            p.text(self.label, self.rect.center, 14, fg, "medium", anchor="center")


class Switch(Widget):
    """Arco switch with a label on the right; the whole row is clickable."""

    TRACK_W, TRACK_H = 28, 16

    def __init__(self, pos, label, get, set_, enabled=None, width=150):
        super().__init__((pos[0], pos[1], width, 22), enabled)
        self.label = label
        self.get = get
        self.set = set_

    def click(self, pos):
        self.set(not self.get())

    def draw(self, p):
        t = p.theme
        on = self.get()
        track = pygame.Rect(self.rect.x, self.rect.centery - self.TRACK_H // 2, self.TRACK_W, self.TRACK_H)
        color = t["primary"] if on else t["switch_off"]
        if not self.enabled:
            color = t["primary_light2"] if on else t["fill3"]
        p.box(track, color, radius=self.TRACK_H // 2)
        knob_x = track.right - 8 if on else track.x + 8
        p.circle((knob_x, track.centery), 6, (255, 255, 255))
        label_color = t["text1"] if self.enabled else t["text4"]
        p.text(self.label, (track.right + 10, self.rect.centery), 14, label_color, anchor="midleft")


class Segmented(Widget):
    """Arco radio-button group: one option highlighted inside a grey track."""

    def __init__(self, rect, options, get, set_):
        super().__init__(rect)
        self.options = options  # list of (key, label)
        self.get = get
        self.set = set_

    def _item_rects(self):
        inner = self.rect.inflate(-6, -6)
        w = inner.width / len(self.options)
        return [pygame.Rect(round(inner.x + i * w), inner.y, round(w), inner.height) for i in range(len(self.options))]

    def click(self, pos):
        for (key, _), r in zip(self.options, self._item_rects()):
            if r.collidepoint(pos):
                self.set(key)

    def draw(self, p):
        t = p.theme
        p.box(self.rect, t["fill2"], radius=4)
        mouse = pygame.mouse.get_pos()
        for (key, label), r in zip(self.options, self._item_rects()):
            selected = key == self.get()
            if selected:
                p.box(r, t["card"], radius=3)
            elif self.hover and r.collidepoint(mouse):
                p.box(r, t["fill3"], radius=3)
            color = t["primary"] if selected else t["text2"]
            p.text(label, r.center, 13, color, "medium" if selected else "regular", anchor="center")


class Stepper(Widget):
    """Arco InputNumber with -/+ buttons."""

    def __init__(self, rect, get, set_, min_value, max_value):
        super().__init__(rect)
        self.get = get
        self.set = set_
        self.min = min_value
        self.max = max_value

    def _parts(self):
        h = self.rect.height
        minus = pygame.Rect(self.rect.x, self.rect.y, h, h)
        plus = pygame.Rect(self.rect.right - h, self.rect.y, h, h)
        return minus, plus

    def click(self, pos):
        minus, plus = self._parts()
        value = self.get()
        if minus.collidepoint(pos) and value > self.min:
            self.set(value - 1)
        elif plus.collidepoint(pos) and value < self.max:
            self.set(value + 1)

    def draw(self, p):
        t = p.theme
        minus, plus = self._parts()
        value = self.get()
        mouse = pygame.mouse.get_pos()
        p.box(self.rect, t["fill2"], radius=4)
        for part, sign, can in ((minus, "-", value > self.min), (plus, "+", value < self.max)):
            if can and part.collidepoint(mouse):
                p.box(part, t["fill3"], radius=4)
            color = t["text1"] if can else t["text4"]
            cx, cy = part.center
            p.line((cx - 5, cy), (cx + 5, cy), color, 2)
            if sign == "+":
                p.line((cx, cy - 5), (cx, cy + 5), color, 2)
        p.text(str(value), self.rect.center, 14, t["text1"], "medium", anchor="center")
