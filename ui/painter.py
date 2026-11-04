import os
import pygame
import pygame.freetype
import pygame.gfxdraw

from ui.theme import LIGHT
from ui.paths import asset

# Bundled Pretendard (SIL OFL, see assets/fonts/LICENSE.txt): covers Latin and Hangul,
# so text looks the same on macOS, Windows and Linux.
_FONTS = {
    "regular": asset("fonts", "Pretendard-Regular.otf"),
    "medium": asset("fonts", "Pretendard-Medium.otf"),
    "bold": asset("fonts", "Pretendard-Bold.otf"),
}


def _clean(text):
    """Turns messages into text and drops emoji the UI fonts cannot draw (keeps Hangul)."""
    text = str(text)
    return "".join(
        ch for ch in text
        if not (0x2600 <= ord(ch) <= 0x27BF or ord(ch) >= 0x1F000 or 0xFE00 <= ord(ch) <= 0xFE0F)
    ).strip()


class Painter:
    """
    Drawing helpers shared by the renderer and widgets.

    Callers work in logical coordinates (the 1200x800 layout). The target surface may be
    larger (e.g. 2x on Retina screens); everything is multiplied by `k` when drawn, so
    text and sprites stay sharp.
    """

    def __init__(self, screen, logical_width):
        pygame.freetype.init()
        self.screen = screen
        self.k = screen.get_width() / logical_width
        self.theme = LIGHT
        self._fonts = {}

    # ------------------------------------------------------------------
    # Scaling
    # ------------------------------------------------------------------
    def s(self, value):
        return round(value * self.k)

    def rect(self, rect):
        r = pygame.Rect(rect)
        x, y = self.s(r.x), self.s(r.y)
        return pygame.Rect(x, y, self.s(r.right) - x, self.s(r.bottom) - y)

    def point(self, pos):
        return (self.s(pos[0]), self.s(pos[1]))

    def scale_image(self, img, size):
        """Scales a source image to a logical size at full output resolution."""
        return pygame.transform.smoothscale(img, (self.s(size[0]), self.s(size[1])))

    # ------------------------------------------------------------------
    # Text
    # ------------------------------------------------------------------
    def font(self, size, weight="regular", text=""):
        key = (size, weight)
        if key not in self._fonts:
            px = self.s(size)
            path = _FONTS[weight]
            if os.path.exists(path):
                f = pygame.freetype.Font(path, px)
            else:
                f = pygame.freetype.Font(None, px)
                f.strong = weight != "regular"
            f.origin = True
            f.pad = False
            self._fonts[key] = f
        return self._fonts[key]

    def text_width(self, text, size=14, weight="regular"):
        text = _clean(text)
        return self.font(size, weight, text).get_rect(text).width / self.k

    def text(self, text, pos, size=14, color=None, weight="regular", anchor="topleft"):
        """Draws one line of text. `anchor` works like pygame.Rect attributes (topleft, center, midright...)."""
        text = _clean(text)
        f = self.font(size, weight, text)
        color = color or self.theme["text1"]
        px = self.s(size)
        asc, desc = f.get_sized_ascender(px), f.get_sized_descender(px)
        width = f.get_rect(text).width if text else 0
        box = pygame.Rect(0, 0, width, asc - desc)
        setattr(box, anchor, self.point(pos))
        if text:
            f.render_to(self.screen, (box.x, box.y + asc), text, color)
        k = self.k
        return pygame.Rect(round(box.x / k), round(box.y / k), round(box.width / k), round(box.height / k))

    def wrap(self, text, max_width, size=14, weight="regular"):
        words = _clean(text).split()
        lines, line = [], ""
        for word in words:
            trial = f"{line} {word}".strip()
            if self.text_width(trial, size, weight) <= max_width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    # ------------------------------------------------------------------
    # Shapes & images
    # ------------------------------------------------------------------
    def box(self, rect, color=None, radius=4, border=None, border_width=1):
        r = self.rect(rect)
        rad = self.s(radius)
        if color is not None:
            pygame.draw.rect(self.screen, color, r, border_radius=rad)
        if border is not None:
            pygame.draw.rect(self.screen, border, r, width=max(1, self.s(border_width)), border_radius=rad)
        return pygame.Rect(rect)

    def alpha_box(self, rect, rgba, radius=0):
        r = self.rect(rect)
        surf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, rgba, surf.get_rect(), border_radius=self.s(radius))
        self.screen.blit(surf, r.topleft)

    def alpha_ellipse(self, rect, rgba):
        r = self.rect(rect)
        surf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.ellipse(surf, rgba, surf.get_rect())
        self.screen.blit(surf, r.topleft)

    def line(self, start, end, color, width=1):
        pygame.draw.line(self.screen, color, self.point(start), self.point(end), max(1, self.s(width)))

    def circle(self, center, radius, color):
        x, y = self.point(center)
        r = self.s(radius)
        pygame.gfxdraw.filled_circle(self.screen, x, y, r, color)
        pygame.gfxdraw.aacircle(self.screen, x, y, r, color)

    def triangle(self, center, size, direction, color):
        """Small arrow-head pointing UP / DOWN / LEFT / RIGHT."""
        x, y = center
        s = size
        points = {
            "UP": [(x, y - s * 0.6), (x - s, y + s * 0.5), (x + s, y + s * 0.5)],
            "DOWN": [(x, y + s * 0.6), (x - s, y - s * 0.5), (x + s, y - s * 0.5)],
            "LEFT": [(x - s * 0.6, y), (x + s * 0.5, y - s), (x + s * 0.5, y + s)],
            "RIGHT": [(x + s * 0.6, y), (x - s * 0.5, y - s), (x - s * 0.5, y + s)],
        }[direction]
        points = [self.point(pt) for pt in points]
        pygame.gfxdraw.filled_polygon(self.screen, points, color)
        pygame.gfxdraw.aapolygon(self.screen, points, color)

    def blit(self, img, **anchor):
        """Blits an image prepared with scale_image; `anchor` is in logical coordinates."""
        if img is None:
            return
        k = self.k
        r = pygame.Rect(0, 0, round(img.get_width() / k), round(img.get_height() / k))
        for name, value in anchor.items():
            setattr(r, name, value)
        self.screen.blit(img, self.point(r.topleft))

    def tag(self, text, pos, fg, bg, size=12, anchor="topleft", height=22, weight="medium"):
        """Arco-style tag: small rounded label with tinted background."""
        width = round(self.text_width(text, size, weight)) + 16
        rect = pygame.Rect(0, 0, width, height)
        setattr(rect, anchor, pos)
        self.box(rect, bg, radius=4)
        self.text(text, rect.center, size, fg, weight, anchor="center")
        return rect
