"""
Color tokens in the spirit of the Arco Design System (light and dark).
Dark-mode "light" fills are Arco's translucent tints pre-blended onto the dark card color.
"""

LIGHT = {
    "name": "light",
    "bg": (242, 243, 245),
    "card": (255, 255, 255),
    "border": (229, 230, 235),
    "text1": (29, 33, 41),
    "text2": (78, 89, 105),
    "text3": (134, 144, 156),
    "text4": (201, 205, 212),
    "fill1": (247, 248, 250),
    "fill2": (242, 243, 245),
    "fill3": (229, 230, 235),
    "fill4": (201, 205, 212),
    "on_primary": (255, 255, 255),
    "primary": (22, 93, 255),
    "primary_hover": (64, 128, 255),
    "primary_active": (14, 66, 210),
    "primary_light": (232, 243, 255),
    "primary_light2": (190, 218, 255),
    "success": (0, 180, 42),
    "success_light": (232, 255, 234),
    "warning": (255, 125, 0),
    "warning_light": (255, 247, 232),
    "danger": (245, 63, 63),
    "danger_light": (255, 236, 232),
    "gold": (247, 186, 30),
    "gold_light": (255, 252, 232),
    "cyan": (20, 201, 201),
    "cyan_light": (232, 255, 251),
    "fog": (229, 230, 235),
    "fog_text": (169, 174, 184),
    "switch_off": (201, 205, 212),
    "overlay": (255, 255, 255, 190),
}

DARK = {
    "name": "dark",
    "bg": (23, 23, 26),
    "card": (35, 35, 36),
    "border": (51, 51, 54),
    "text1": (233, 233, 233),
    "text2": (190, 190, 191),
    "text3": (145, 145, 146),
    "text4": (99, 99, 100),
    "fill1": (43, 43, 44),
    "fill2": (52, 52, 53),
    "fill3": (62, 62, 63),
    "fill4": (77, 77, 78),
    "on_primary": (255, 255, 255),
    "primary": (60, 126, 255),
    "primary_hover": (104, 159, 255),
    "primary_active": (41, 98, 220),
    "primary_light": (40, 53, 80),
    "primary_light2": (44, 67, 113),
    "success": (39, 195, 70),
    "success_light": (36, 67, 43),
    "warning": (255, 150, 38),
    "warning_light": (79, 58, 36),
    "danger": (247, 105, 101),
    "danger_light": (77, 49, 49),
    "gold": (249, 204, 69),
    "gold_light": (78, 69, 43),
    "cyan": (48, 201, 201),
    "cyan_light": (38, 68, 69),
    "fog": (44, 44, 46),
    "fog_text": (99, 99, 100),
    "switch_off": (77, 77, 78),
    "overlay": (23, 23, 26, 200),
}


def _os_prefers_dark():
    """Best-effort read of the OS light/dark setting; None when it cannot be determined."""
    import subprocess
    import sys

    def run(*cmd):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
            return out.returncode, out.stdout.strip().lower()
        except (OSError, subprocess.SubprocessError):
            return None, ""

    if sys.platform == "darwin":
        # The key exists (with value "Dark") only while dark mode is on.
        code, out = run("defaults", "read", "-g", "AppleInterfaceStyle")
        return code == 0 and "dark" in out if code is not None else None
    if sys.platform.startswith("win"):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0
        except OSError:
            return None
    # Linux / BSD desktops (GNOME, and others that honour the freedesktop key)
    code, out = run("gsettings", "get", "org.gnome.desktop.interface", "color-scheme")
    if code == 0 and out:
        return "dark" in out
    code, out = run("gsettings", "get", "org.gnome.desktop.interface", "gtk-theme")
    if code == 0 and out:
        return "dark" in out
    return None


def system_theme():
    """Theme matching the OS appearance (light when unknown). Users can still toggle it."""
    return DARK if _os_prefers_dark() else LIGHT


class _OSWatcher:
    """Polls the OS appearance in a background thread; `version` bumps on every change."""

    INTERVAL = 1.5  # seconds

    def __init__(self):
        import threading
        self.dark = bool(_os_prefers_dark())
        self.version = 0
        threading.Thread(target=self._loop, name="os-theme-watcher", daemon=True).start()

    def _loop(self):
        import time
        while True:
            time.sleep(self.INTERVAL)
            value = _os_prefers_dark()
            if value is not None and value != self.dark:
                self.dark = value
                self.version += 1


_watcher = None


def os_watcher():
    """Shared watcher, started on first use."""
    global _watcher
    if _watcher is None:
        _watcher = _OSWatcher()
    return _watcher


def blend(a, b, t):
    """Theme halfway between `a` and `b` (t = 0..1), used for the crossfade."""
    out = {}
    for key, vb in b.items():
        va = a.get(key, vb)
        if isinstance(vb, tuple) and isinstance(va, tuple) and len(va) == len(vb):
            out[key] = tuple(round(x + (y - x) * t) for x, y in zip(va, vb))
        else:
            out[key] = vb
    return out
