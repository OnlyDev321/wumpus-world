"""Compare route planners under both agent policies on identical maps.

Run from the project root, for example:
    python -m game.search_benchmark --games 200

The benchmark writes one summary CSV row per policy, room count, and planner.
All combinations receive the same map seeds within each room count.
"""

import argparse
import csv
import time

from game.agent import Agent
from game.algorithms import SafeOnlyAgent
from game.benchmarking import BASE_SEED, CSV_FIELDS, play_one, summarize_results
from game.world import World

PLANNERS = ("bfs", "ucs", "auto")
POLICIES = {"logic-risk": Agent, "safe-only": SafeOnlyAgent}
POLICY_LABELS = {"logic-risk": "Logic + risk", "safe-only": "Safe only"}


def planner_agent(planner, policy):
    """Create an agent class combining the selected policy and route planner."""
    policy_class = POLICIES[policy]

    class BenchmarkAgent(policy_class):
        def _select_search_algorithm(self, goals, allow_shot, can_shoot):
            if planner == "auto":
                return super()._select_search_algorithm(goals, allow_shot, can_shoot)
            return planner

    BenchmarkAgent.__name__ = f"{policy}_{planner.upper()}BenchmarkAgent"
    return BenchmarkAgent


def run(games):
    rows = []
    for room_count in range(World.MIN_ROOMS, World.MAX_ROOMS + 1):
        for policy in POLICIES:
            for planner in PLANNERS:
                agent_class = planner_agent(planner, policy)
                started = time.perf_counter()
                results = [
                    play_one(agent_class, room_count, BASE_SEED + index)
                    for index in range(games)
                ]
                row = {
                    "rooms": room_count,
                    "strategy": POLICY_LABELS[policy],
                    "route_planner": planner,
                    **summarize_results(results),
                    "elapsed_seconds": time.perf_counter() - started,
                }
                rows.append(row)
                print(
                    f"{room_count:>5} {policy:>11} {planner.upper():>7}"
                    f" {row['win_rate']:>7.1%} {row['pit_rate']:>7.1%}"
                    f" {row['avg_steps']:>9.1f} {row['avg_score']:>9.1f}"
                    f" {row['think_ms_per_decision']:>10.3f}",
                    flush=True,
                )
    return rows


def main():
    parser = argparse.ArgumentParser(description="Compare route planners on identical Wumpus maps.")
    parser.add_argument("--games", type=int, default=100, help="maps per room count and planner")
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be at least 1")

    output_path = "search_benchmark.csv"
    print(f"{args.games} maps per policy/room/planner; shared seeds starting at {BASE_SEED}")
    print(f"{'Rooms':>5} {'Policy':>11} {'Planner':>7} {'Win':>7} {'Pit':>7}"
          f" {'Steps':>9} {'Score':>9} {'ms/decision':>10}")
    started = time.perf_counter()
    rows = run(args.games)
    with open(output_path, "w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} summary rows to {output_path}")
    print(f"Elapsed: {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
