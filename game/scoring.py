"""Point values shared by the game and the agent's route planner."""

MOVE_COST = 1
SHOT_COST = 10
DEATH_COST = 1000
GOLD_REWARD = 1000

# Fixed memory penalty costs by cause. These do not depend on the room/floor.
PIT_PENALTY = 50
WUMPUS_PENALTY = 100


def calculate_memory_penalty(death_memory, world=None):
    """
    Calculates the starting penalty for cross-episode death memory.

    The penalty is fixed by the cause of death and independent of the
    room/floor where the hazard was found:
      - Pit: 50 points per remembered pit
      - Wumpus: 100 points

    ``world`` remains optional for compatibility with existing callers.
    """
    if not death_memory:
        return 0
    total = 0
    total += PIT_PENALTY * len(death_memory.get("pits", ()))
    if death_memory.get("wumpus") is not None:
        total += WUMPUS_PENALTY
    return total

