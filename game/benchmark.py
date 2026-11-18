"""
Headless strategy benchmark: plays many games without graphics and summarizes results.

Each strategy is tested on the same maps within each room count. The agent's
route planner is Auto, which selects BFS or UCS for each planning task.

Command line:
    python -m game.benchmark --games 200
"""
import argparse
import csv
import time

from game.world import World
from game.algorithms import ALGORITHMS
from game.benchmarking import BASE_SEED, CSV_FIELDS, play_one, summarize_results


def summarize(results):
    metrics = summarize_results(results)
    if metrics is None:
        return None
    return {
        "games": metrics["games"],
        "win": metrics["win_rate"],
        "pit": metrics["pit_rate"],
        "wumpus": metrics["wumpus_rate"],
        "escaped": metrics["escaped_rate"],
        "trapped": metrics["trapped_rate"],
        "kills": metrics["kills_rate"],
        "score": metrics["avg_score"],
        "steps": metrics["avg_steps"],
        "explored": metrics["avg_explored"],
        "think_ms": metrics["think_ms_per_decision"],
        "think_ms_max": metrics["think_ms_max"],
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
    parser = argparse.ArgumentParser(description="Compare Wumpus World agent strategies on identical maps.")
    parser.add_argument("--games", type=int, default=100,
                        help="maps per strategy and room count (default: 100)")
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be at least 1")

    rooms_to_test = range(World.MIN_ROOMS, World.MAX_ROOMS + 1)
    names = list(ALGORITHMS)
    output_path = "strategy_benchmark.csv"
    print(f"{args.games} games per strategy and room count; route planner: Auto\n")
    print(f"{'Rooms':<7}{'Strategy':<16}{'Win':>7}{'Pit':>7}{'Wumpus':>8}{'Escaped':>9}{'Trapped':>9}{'Kills':>7}"
          f"{'Score':>9}{'Steps':>8}{'Explored':>10}{'ms/step':>9}{'Time':>8}")
    rows = []
    for rooms in rooms_to_test:
        for name in names:
            bench = Benchmark(name, rooms, args.games)
            while not bench.done:
                bench.step(1000)
            s = bench.summary()
            rows.append({
                "rooms": rooms,
                "strategy": name,
                "route_planner": "auto",
                "games": s["games"],
                "win_rate": s["win"],
                "pit_rate": s["pit"],
                "wumpus_rate": s["wumpus"],
                "escaped_rate": s["escaped"],
                "trapped_rate": s["trapped"],
                "kills_rate": s["kills"],
                "avg_score": s["score"],
                "avg_steps": s["steps"],
                "avg_explored": s["explored"],
                "think_ms_per_decision": s["think_ms"],
                "think_ms_max": s["think_ms_max"],
                "elapsed_seconds": s["seconds"],
            })
            print(f"{rooms:<7}{name:<16}{s['win']:>7.0%}{s['pit']:>7.0%}{s['wumpus']:>8.0%}{s['escaped']:>9.0%}"
                  f"{s['trapped']:>9.0%}{s['kills']:>7.0%}{s['score']:>9.0f}{s['steps']:>8.1f}{s['explored']:>10.0%}"
                  f"{s['think_ms']:>9.2f}{s['seconds']:>7.1f}s")

    with open(output_path, "w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} summary rows to {output_path}")


if __name__ == "__main__":
    main()
