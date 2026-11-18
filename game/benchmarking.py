"""Shared helpers and output schema for headless benchmark commands."""

import random

from game.game_manager import GameManager
from game.world import World

BASE_SEED = 1000
MAX_STEPS = 2000
CSV_FIELDS = [
    "rooms", "strategy", "route_planner", "games", "win_rate", "pit_rate",
    "wumpus_rate", "escaped_rate", "trapped_rate", "kills_rate", "avg_score",
    "avg_steps", "avg_explored", "think_ms_per_decision", "think_ms_max",
    "elapsed_seconds",
]


def play_one(agent_class, rooms, seed):
    """Play one seeded episode and restore the process-wide random state."""
    random_state = random.getstate()
    random.seed(seed)
    try:
        world = World(num_rooms=rooms)
        manager = GameManager(world, agent_class(world))
        for _ in range(MAX_STEPS):
            if manager.game_over:
                break
            manager.step_ai()
        if not manager.game_over:
            manager.game_over, manager.death_reason = True, "TRAPPED"
            manager._after_action()
        return manager.history[-1]
    finally:
        random.setstate(random_state)


def summarize_results(results):
    """Return shared benchmark metrics with the common CSV column names."""
    count = len(results)
    if not count:
        return None

    decisions = sum(result["decisions"] for result in results)
    return {
        "games": count,
        "win_rate": sum(result["outcome"] == "win" for result in results) / count,
        "pit_rate": sum(result["outcome"] == "pit" for result in results) / count,
        "wumpus_rate": sum(result["outcome"] == "wumpus" for result in results) / count,
        "escaped_rate": sum(result["outcome"] == "escaped" for result in results) / count,
        "trapped_rate": sum(result["outcome"] == "trapped" for result in results) / count,
        "kills_rate": sum(result["kills"] > 0 for result in results) / count,
        "avg_score": sum(result["score"] for result in results) / count,
        "avg_steps": sum(result["steps"] for result in results) / count,
        "avg_explored": sum(result["explored"] for result in results) / count,
        "think_ms_per_decision": (
            sum(result["think_ms_avg"] * result["decisions"] for result in results) / decisions
            if decisions else 0.0
        ),
        "think_ms_max": max(result["think_ms_max"] for result in results),
    }
