"""
Game recordings: the starting map plus every action, enough to replay a game exactly.

The live game (main.py) saves each finished game; only the last MAX_GAMES are kept in
replays/recent_games.json. replay_viewer.py lists them and plays them back with the
game's own GameManager and Renderer, so a replay looks exactly like the original game.
"""
import json
import os
import time
from datetime import datetime

from game.world import World
from game.agent import Agent
from game.algorithms import ALGORITHMS
from game.game_manager import GameManager

MAX_GAMES = 10
REPLAYS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "replays", "recent_games.json")


class ReplayStore:
    """The saved games file, newest game first."""

    def __init__(self, path=REPLAYS_FILE, max_games=MAX_GAMES):
        self.path = path
        self.max_games = max_games

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                games = json.load(f)
        except (OSError, ValueError):
            return []
        return games if isinstance(games, list) else []

    def add(self, record):
        """Saves a game and drops the oldest ones. Returns False when the file could not be written."""
        games = ([record] + self.load())[: self.max_games]
        tmp = self.path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(games, f, ensure_ascii=False)
            os.replace(tmp, self.path)  # never leaves a half-written file behind
        except OSError as e:
            print(f"Could not save replay to {self.path}: {e}")
            return False
        return True

    def modified(self):
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return None


class GameRecorder:
    """Attached to the live GameManager: records the current game and saves it when it ends."""

    def __init__(self, store=None):
        self.store = store or ReplayStore()
        self.record = None
        self._t0 = 0.0

    def start(self, gm, retry=False):
        memory = gm.agent.death_memory
        self._t0 = time.perf_counter()
        self.record = {
            "version": 1,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "algorithm": gm.algorithm,
            "map": gm.map_kind,
            "retry": retry,
            "rooms": gm.world.num_rooms,
            "layout": gm.world.to_layout(),
            "death_memory": {
                "pits": sorted(list(cell) for cell in memory["pits"]),
                "wumpus": list(memory["wumpus"]) if memory["wumpus"] else None,
            },
            "events": [],
        }

    def add(self, kind, **data):
        if self.record is not None:
            self.record["events"].append({"kind": kind, "t": round(time.perf_counter() - self._t0, 3), **data})

    def finish(self, gm):
        """Saves the finished game. Returns True when it was written to disk."""
        if self.record is None:
            return False
        record, self.record = self.record, None
        kinds = {event["kind"] for event in record["events"]}
        ai, player = "ai" in kinds, bool(kinds - {"ai"})
        record["control"] = "mixed" if ai and player else ("manual" if player else "ai")
        record["finished_at"] = datetime.now().isoformat(timespec="seconds")
        record["result"] = gm.result()
        return self.store.add(record)


class Replay:
    """Plays a saved game back on a fresh GameManager; `seek` moves to any point of the game."""

    def __init__(self, record):
        self.record = record
        self.events = record["events"]
        self.position = 0  # number of events applied
        self.gm = self._fresh()

    def _fresh(self):
        world = World.from_layout(self.record["layout"])
        memory = self.record["death_memory"]
        death_memory = {"pits": {tuple(cell) for cell in memory["pits"]},
                        "wumpus": tuple(memory["wumpus"]) if memory["wumpus"] else None}
        agent_class = ALGORITHMS.get(self.record["algorithm"], Agent)
        return GameManager(world, agent_class(world, death_memory=death_memory))

    @property
    def length(self):
        return len(self.events)

    @property
    def at_end(self):
        return self.position >= self.length

    def seek(self, position):
        position = max(0, min(self.length, position))
        if position < self.position:
            # Actions cannot be undone: replay from the start (games are short, this is instant)
            self.gm = self._fresh()
            self.position = 0
        while self.position < position:
            self._apply(self.events[self.position])
            self.position += 1

    def step(self, delta=1):
        self.seek(self.position + delta)

    def _apply(self, event):
        gm, kind = self.gm, event["kind"]
        if kind == "ai":
            action = dict(event["action"])
            if "to" in action:
                action["to"] = tuple(action["to"])
            gm.step_ai(action=action)
        elif kind == "move":
            gm.manual_move(event["dr"], event["dc"])
        elif kind == "grab":
            gm.manual_grab()
        elif kind == "shoot":
            gm.manual_shoot(event["direction"])
        elif kind == "climb":
            gm.manual_climb()
        elif kind == "door":
            gm.manual_enter_door()
