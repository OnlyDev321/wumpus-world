"""
Propositional Logic Reasoning System for Wumpus World AI.
"""

# Chance that an unexplored cell holds a pit (matches World.pit_prob)
PIT_PRIOR = 0.15
# Largest group of linked breeze candidates solved exactly (2**n layouts are checked)
MAX_EXACT_CELLS = 14


def deduce_knowledge(cells, neighbors, visited, percepts_history, is_wumpus_alive=True, death_memory=None, missed_shots=None):
    """
    Deduces knowledge based on observation history and cross-episode death memory:
    - cells: all cells of the dungeon
    - neighbors: function pos -> cells reachable in one step (walls and doors respected)
    - visited: set of cells visited by Agent (100% safe)
    - percepts_history: dict {pos: set(percepts)}
    - is_wumpus_alive: bool
    - death_memory: optional dict containing {"pits": set(), "wumpus": tuple or None}
    - missed_shots: optional set of cells traversed by missed arrow shots (guaranteed Wumpus-Free)

    Returns:
    - safe_cells: set of cells definitively SAFE
    - confirmed_pits: set of cells definitively containing PITS
    - confirmed_wumpus: cell definitively containing WUMPUS (or None if uncertain)
    - possible_pits: set of candidate PIT cells
    - possible_wumpus: set of candidate WUMPUS cells
    - pit_free: set of cells guaranteed to have no Pit
    - wumpus_free: set of cells guaranteed to have no Wumpus
    """
    all_cells = set(cells)

    # Extract hazards learned from previous deaths in this world
    recalled_pits = set(death_memory.get("pits", set())) if death_memory else set()
    recalled_wumpus = death_memory.get("wumpus") if death_memory else None

    # 1. Cells guaranteed to be free of Pits (Pit-Free)
    pit_free = set(visited)
    for pos in visited:
        percepts = percepts_history.get(pos, set())
        # If no Breeze, all adjacent cells are guaranteed to have no Pit
        if "breeze" not in percepts:
            for neighbor in neighbors(pos):
                pit_free.add(neighbor)

    # Any recalled fatal pit must never be considered pit_free
    pit_free -= recalled_pits

    # 2. Cells guaranteed to be free of Wumpus (Wumpus-Free)
    wumpus_free = set(visited)
    if missed_shots:
        wumpus_free |= set(missed_shots)
    if not is_wumpus_alive:
        # If Wumpus is dead, the entire world is free of Wumpus threat
        wumpus_free = set(all_cells)
    else:
        for pos in visited:
            percepts = percepts_history.get(pos, set())
            # If no Stench, all adjacent cells are guaranteed to have no Wumpus
            if "stench" not in percepts:
                for neighbor in neighbors(pos):
                    wumpus_free.add(neighbor)

    # 3. Deduce Wumpus location (Only exactly 1 Wumpus exists in the world)
    confirmed_wumpus = None
    possible_wumpus = set()
    # True when the Wumpus is known to be among possible_wumpus. Without a stench the agent
    # cannot tell, because `cells` holds only the rooms it has seen so far.
    wumpus_localized = False

    if is_wumpus_alive:
        if recalled_wumpus:
            # Learned from previous death by Wumpus
            wumpus_localized = True
            confirmed_wumpus = recalled_wumpus
            wumpus_free = all_cells - {recalled_wumpus}
            possible_wumpus = {recalled_wumpus}
        else:
            stench_positions = [pos for pos in visited if "stench" in percepts_history.get(pos, set())]
            if stench_positions:
                # Wumpus must be located in the intersection of candidate cells for all Stench positions
                wumpus_localized = True
                candidate_sets = []
                for sp in stench_positions:
                    candidates = set(neighbors(sp)) - wumpus_free
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
                # No Stench encountered yet: any known cell not ruled out may hold the Wumpus,
                # and so may any room not discovered yet
                possible_wumpus = all_cells - wumpus_free

    # 4. Deduce Pit locations (Multiple Pits can exist)
    # Start with confirmed pits from episodic death memory
    confirmed_pits = set(recalled_pits)
    possible_pits = set(recalled_pits)
    breeze_positions = [pos for pos in visited if "breeze" in percepts_history.get(pos, set())]

    breeze_candidates = []
    for bp in breeze_positions:
        candidates = set(neighbors(bp)) - pit_free
        if len(candidates) == 1:
            # Only one unknown neighbor adjacent to a breeze cell -> Definitely a Pit
            confirmed_pits.update(candidates)
        possible_pits.update(candidates)
        breeze_candidates.append(candidates)

    # Chance of a pit in each candidate cell, given every breeze seen so far.
    pit_chance = pit_probabilities(breeze_candidates, recalled_pits)

    # 5. Determine definitively SAFE cells
    # Safe cell = Pit-Free AND Wumpus-Free (recalled fatal pits are strictly excluded)
    safe_cells = pit_free.intersection(wumpus_free) - confirmed_pits

    return {
        "safe_cells": safe_cells,
        "confirmed_pits": confirmed_pits,
        "confirmed_wumpus": confirmed_wumpus,
        "possible_pits": possible_pits,
        "possible_wumpus": possible_wumpus,
        "wumpus_localized": wumpus_localized,
        "pit_free": pit_free,
        "wumpus_free": wumpus_free,
        "pit_chance": pit_chance,
    }


def pit_probabilities(constraints, known_pits=(), prior=PIT_PRIOR, max_cells=MAX_EXACT_CELLS):
    """
    Chance of a pit in every cell named by `constraints`.

    Each constraint is the set of unknown cells next to one breeze: at least one of them
    holds a pit. Pits are independent with chance `prior`, so the answer comes from
    weighing every pit layout that satisfies all constraints. Cells in `known_pits` are
    pits for sure. Constraints that share no cell are solved separately; a group larger
    than `max_cells` falls back to an estimate of 1/k per breeze.
    """
    known_pits = set(known_pits)
    open_constraints = [set(c) - known_pits for c in constraints if not set(c) & known_pits]
    chances = {cell: 1.0 for c in constraints for cell in set(c) & known_pits}

    # Group constraints that share cells (connected components)
    groups = []
    for constraint in open_constraints:
        merged = [g for g in groups if g[0] & constraint]
        cells, members = set(constraint), [constraint]
        for g in merged:
            groups.remove(g)
            cells |= g[0]
            members += g[1]
        groups.append((cells, members))

    for constraint in constraints:
        for cell in set(constraint) - known_pits:
            chances.setdefault(cell, prior)  # cells whose breeze is already explained

    for cells, members in groups:
        order = sorted(cells)
        if len(order) > max_cells:
            for constraint in members:
                for cell in constraint:
                    chances[cell] = max(chances.get(cell, 0), 1 / len(constraint))
            continue
        bit = {cell: 1 << i for i, cell in enumerate(order)}
        masks = [sum(bit[cell] for cell in constraint) for constraint in members]
        n = len(order)
        weight_of = [prior ** k * (1 - prior) ** (n - k) for k in range(n + 1)]
        total = 0.0
        per_cell = [0.0] * n
        for layout in range(1 << n):
            if all(layout & mask for mask in masks):
                weight = weight_of[layout.bit_count()]
                total += weight
                for i in range(n):
                    if layout >> i & 1:
                        per_cell[i] += weight
        for i, cell in enumerate(order):
            chances[cell] = round(per_cell[i] / total, 6)
    return chances


def calculate_cell_risk(cell, knowledge):
    """
    Estimated chance (0..1) that an unvisited cell is deadly, used when no 100% safe cells remain.
    0: definitively safe, 10: confirmed hazard (never chosen).
    """
    if cell in knowledge["safe_cells"]:
        return 0
    if cell in knowledge["confirmed_pits"] or knowledge["confirmed_wumpus"] == cell:
        return 10

    pit = 0
    if cell in knowledge["possible_pits"]:
        pit = knowledge.get("pit_chance", {}).get(cell, PIT_PRIOR)
    elif cell not in knowledge["pit_free"]:
        pit = PIT_PRIOR

    wumpus = 0
    possible_wumpus = knowledge["possible_wumpus"]
    if cell in possible_wumpus:
        wumpus = 1 / len(possible_wumpus)

    return round(1 - (1 - pit) * (1 - wumpus), 3)
