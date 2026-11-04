import os

# Absolute path to the project's assets folder, so the game runs from any working directory.
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def asset(*parts):
    return os.path.join(ASSETS_DIR, *parts)
