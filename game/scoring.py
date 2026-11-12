"""Point values shared by the game and the agent's route planner."""

MOVE_COST = 1
SHOT_COST = 10
DEATH_COST = 1000
GOLD_REWARD = 1000

# Base memory penalty costs per room floor (escalates as Base * Floor)
PIT_BASE_PENALTY = 20
WUMPUS_BASE_PENALTY = 50


def calculate_memory_penalty(death_memory, world):
    """
    Calculates starting memory debt penalty for cross-episode death memory:
    Penalty scales with the room floor (1-based):
      - Pit: PIT_BASE_PENALTY * floor (Room 1: 20, Room 2: 40, ..., Room 6: 120)
      - Wumpus: WUMPUS_BASE_PENALTY * floor (Room 1: 50, Room 2: 100, ..., Room 6: 300)
    """
    if not death_memory:
        return 0
    total = 0
    for pit in death_memory.get("pits", ()):
        floor = world.room_of(pit) + 1 if hasattr(world, "room_of") else 1
        total += PIT_BASE_PENALTY * floor
    wumpus = death_memory.get("wumpus")
    if wumpus:
        floor = world.room_of(wumpus) + 1 if hasattr(world, "room_of") else 1
        total += WUMPUS_BASE_PENALTY * floor
    return total

