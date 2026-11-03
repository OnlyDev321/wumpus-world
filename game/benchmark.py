"""
Headless benchmark: plays many games without graphics and summarizes the results.

Every algorithm is tested on the same maps (map i is generated from seed BASE_SEED + i),
so results are directly comparable.

Command line:
    python -m game.benchmark --games 200 --rooms 3
    python -m game.benchmark --games 200 --rooms 3 --algo "Safe only"
"""
import argparse
import random
import time

from game.world import World
from game.game_manager import GameManager
from game.algorithms import ALGORITHMS

BASE_SEED = 1000
MAX_STEPS = 2000


def play_one(agent_class, rooms, seed):
    """Plays one full game on the map generated from `seed`; returns GameManager.result()."""
    state = random.getstate()
    random.seed(seed)
    try:
        world = World(num_rooms=rooms)
    finally:
        random.setstate(state)  # do not disturb the live game's randomness
    gm = GameManager(world, agent_class(world))
    for _ in range(MAX_STEPS):
        if gm.game_over:
            break
        gm.step_ai()
    if not gm.game_over:
        gm.game_over, gm.death_reason = True, "TRAPPED"
        gm._after_action()
    return gm.history[-1]


def summarize(results):
    n = len(results)
    if not n:
        return None
    count = lambda o: sum(r["outcome"] == o for r in results) / n
    decisions = sum(r["decisions"] for r in results)
    return {
        "games": n,
        "win": count("win"),
        "pit": count("pit"),
        "wumpus": count("wumpus"),
        "escaped": count("escaped"),
        "trapped": count("trapped"),
        "kills": sum(r["kills"] > 0 for r in results) / n,
        "score": sum(r["score"] for r in results) / n,
        "steps": sum(r["steps"] for r in results) / n,
        "explored": sum(r["explored"] for r in results) / n,
        "think_ms": sum(r["think_ms_avg"] * r["decisions"] for r in results) / decisions if decisions else 0.0,
        "think_ms_max": max(r["think_ms_max"] for r in results),
    }


class Benchmark:
    """Runs games a few at a time (see `step`) so the UI stays responsive."""

    def __init__(self, algo_name, rooms, games):
        self.algo_name = algo_name
        self.agent_class = ALGORITHMS[algo_name]
        self.rooms = rooms
        self.games = games
        self.results = []
        self.started = time.perf_counter()
        self.seconds = 0.0

    @property
    def done(self):
        return len(self.results) >= self.games

    @property
    def progress(self):
        return len(self.results) / self.games

    def step(self, budget_ms=12):
        deadline = time.perf_counter() + budget_ms / 1000
        while not self.done and time.perf_counter() < deadline:
            self.results.append(play_one(self.agent_class, self.rooms, BASE_SEED + len(self.results)))
        self.seconds = time.perf_counter() - self.started

    def summary(self):
        s = summarize(self.results)
        if s:
            s["seconds"] = self.seconds
        return s


def main():
    parser = argparse.ArgumentParser(description="Compare Wumpus World agents on the same maps.")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--rooms", type=int, default=3)
    parser.add_argument("--algo", action="append", help="algorithm name (repeatable); default: all")
    args = parser.parse_args()

    names = args.algo or list(ALGORITHMS)
    print(f"{args.games} games, {args.rooms} room(s), same maps for every algorithm\n")
    print(f"{'Algorithm':<16}{'Win':>7}{'Pit':>7}{'Wumpus':>8}{'Escaped':>9}{'Trapped':>9}{'Kills':>7}"
          f"{'Score':>9}{'Steps':>8}{'Explored':>10}{'ms/step':>9}{'Time':>8}")
    for name in names:
        bench = Benchmark(name, args.rooms, args.games)
        while not bench.done:
            bench.step(1000)
        s = bench.summary()
        print(f"{name:<16}{s['win']:>7.0%}{s['pit']:>7.0%}{s['wumpus']:>8.0%}{s['escaped']:>9.0%}"
              f"{s['trapped']:>9.0%}{s['kills']:>7.0%}{s['score']:>9.0f}{s['steps']:>8.1f}{s['explored']:>10.0%}"
              f"{s['think_ms']:>9.2f}{s['seconds']:>7.1f}s")


if __name__ == "__main__":
    main()
