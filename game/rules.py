"""
Propositional Logic Reasoning System for Wumpus World AI.
"""


def get_adjacent_cells(pos, size=4):
    """Returns valid adjacent cells (4 directions: Up, Down, Left, Right) within grid size."""
    r, c = pos
    adjacent = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < size and 0 <= nc < size:
            adjacent.append((nr, nc))
    return adjacent


def deduce_knowledge(size, visited, percepts_history, is_wumpus_alive=True):
    """
    Deduces knowledge based on observation history:
    - visited: set of cells visited by Agent (100% safe)
    - percepts_history: dict {pos: set(percepts)}
    - is_wumpus_alive: bool

    Returns:
    - safe_cells: set of cells definitively SAFE
    - confirmed_pits: set of cells definitively containing PITS
    - confirmed_wumpus: cell definitively containing WUMPUS (or None if uncertain)
    - possible_pits: set of candidate PIT cells
    - possible_wumpus: set of candidate WUMPUS cells
    - pit_free: set of cells guaranteed to have no Pit
    - wumpus_free: set of cells guaranteed to have no Wumpus
    """
    all_cells = {(r, c) for r in range(size) for c in range(size)}

    # 1. Cells guaranteed to be free of Pits (Pit-Free)
    pit_free = set(visited)
    for pos in visited:
        percepts = percepts_history.get(pos, set())
        # If no Breeze, all adjacent cells are guaranteed to have no Pit
        if "breeze" not in percepts:
            for neighbor in get_adjacent_cells(pos, size):
                pit_free.add(neighbor)

    # 2. Cells guaranteed to be free of Wumpus (Wumpus-Free)
    wumpus_free = set(visited)
    if not is_wumpus_alive:
        # If Wumpus is dead, the entire world is free of Wumpus threat
        wumpus_free = set(all_cells)
    else:
        for pos in visited:
            percepts = percepts_history.get(pos, set())
            # If no Stench, all adjacent cells are guaranteed to have no Wumpus
            if "stench" not in percepts:
                for neighbor in get_adjacent_cells(pos, size):
                    wumpus_free.add(neighbor)

    # 3. Deduce Wumpus location (Only exactly 1 Wumpus exists in the world)
    confirmed_wumpus = None
    possible_wumpus = set()

    if is_wumpus_alive:
        stench_positions = [pos for pos in visited if "stench" in percepts_history.get(pos, set())]
        if stench_positions:
            # Wumpus must be located in the intersection of candidate cells for all Stench positions
            candidate_sets = []
            for sp in stench_positions:
                candidates = set(get_adjacent_cells(sp, size)) - wumpus_free
                candidate_sets.append(candidates)

            if candidate_sets:
                intersection = set.intersection(*candidate_sets)
                possible_wumpus = intersection

                if len(intersection) == 1:
                    confirmed_wumpus = next(iter(intersection))
                    # Since there is only 1 Wumpus, all other cells are wumpus_free
                    wumpus_free = all_cells - {confirmed_wumpus}
                    possible_wumpus = {confirmed_wumpus}
        else:
            # No Stench encountered yet: any cell not ruled out can potentially hold the Wumpus
            possible_wumpus = all_cells - wumpus_free

    # 4. Deduce Pit locations (Multiple Pits can exist)
    confirmed_pits = set()
    possible_pits = set()
    breeze_positions = [pos for pos in visited if "breeze" in percepts_history.get(pos, set())]

    for bp in breeze_positions:
        candidates = set(get_adjacent_cells(bp, size)) - pit_free
        if len(candidates) == 1:
            # Only one unknown neighbor adjacent to a breeze cell -> Definitely a Pit
            confirmed_pits.update(candidates)
        possible_pits.update(candidates)

    # 5. Determine definitively SAFE cells
    # Safe cell = Pit-Free AND Wumpus-Free
    safe_cells = pit_free.intersection(wumpus_free)

    return {
        "safe_cells": safe_cells,
        "confirmed_pits": confirmed_pits,
        "confirmed_wumpus": confirmed_wumpus,
        "possible_pits": possible_pits,
        "possible_wumpus": possible_wumpus,
        "pit_free": pit_free,
        "wumpus_free": wumpus_free,
    }


def calculate_cell_risk(cell, knowledge):
    """
    Calculates the risk score of an unvisited cell when no 100% safe cells remain.
    Lower values indicate lower danger:
    0: Definitively safe
    1: Might contain either Wumpus or Pit
    2: Might contain both Wumpus and Pit
    10: Definite hazard (Confirmed Pit or Confirmed Wumpus)
    """
    if cell in knowledge["safe_cells"]:
        return 0
    if cell in knowledge["confirmed_pits"]:
        return 10
    if knowledge["confirmed_wumpus"] == cell:
        return 10

    risk = 0
    if cell in knowledge["possible_pits"]:
        risk += 1
    if cell in knowledge["possible_wumpus"]:
        risk += 1
    return risk
