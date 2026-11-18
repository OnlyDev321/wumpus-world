"""Compare route planners under both agent policies on identical maps.

Run from the project root, for example:
    python -m game.search_benchmark --games 200

The benchmark writes one summary CSV row per policy, room count, and planner.
All combinations receive the same map seeds within each room count.
"""

import argparse
import csv
import time
from pathlib import Path

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


def run(games, rooms, planners, policies, base_seed):
    rows = []
    for room_count in rooms:
        for policy in policies:
            for planner in planners:
                agent_class = planner_agent(planner, policy)
                started = time.perf_counter()
                results = [
                    play_one(agent_class, room_count, base_seed + index)
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
    parser.add_argument("--rooms", type=int, nargs="+", default=list(range(1, 7)),
                        choices=range(World.MIN_ROOMS, World.MAX_ROOMS + 1),
                        help="room counts to compare; default: 1 through 6")
    parser.add_argument("--planners", nargs="+", choices=PLANNERS, default=list(PLANNERS),
                        help="planners to compare; default: bfs ucs auto")
    parser.add_argument("--policies", nargs="+", choices=POLICIES,
                        default=list(POLICIES),
                        help="agent policies to compare; default: logic-risk safe-only")
    parser.add_argument("--seed", type=int, default=BASE_SEED, help="first map seed")
    parser.add_argument("--output", type=Path, default=Path("search_benchmark.csv"),
                        help="summary CSV output path")
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be at least 1")

    print(f"{args.games} maps per policy/room/planner; shared seeds starting at {args.seed}")
    print(f"{'Rooms':>5} {'Policy':>11} {'Planner':>7} {'Win':>7} {'Pit':>7}"
          f" {'Steps':>9} {'Score':>9} {'ms/decision':>10}")
    started = time.perf_counter()
    rows = run(args.games, args.rooms, args.planners, args.policies, args.seed)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} summary rows to {args.output.resolve()}")
    print(f"Elapsed: {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
