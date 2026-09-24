from collections import deque
from game.rules import deduce_knowledge, calculate_cell_risk, get_adjacent_cells


class Agent:
    """
    AI Agent implementing the complete loop:
    Perception -> Memory -> Reasoning -> Decision Making -> Action.
    Enhanced with Episodic Memory to retain fatal failure causes across replays.
    """

    def __init__(self, start_pos=(3, 0), size=4, death_memory=None):
        self.size = size
        self.start_pos = start_pos
        self.position = start_pos
        self.has_gold = False
        self.has_arrow = True
        self.is_alive = True
        self.escaped = False

        # Cross-episode memory (persists across map replays)
        self.death_memory = (
            {"pits": set(death_memory.get("pits", set())), "wumpus": death_memory.get("wumpus")}
            if death_memory is not None
            else {"pits": set(), "wumpus": None}
        )

        # In-episode memory
        self.visited = set()
        self.percepts_history = {}
        self.knowledge = {
            "safe_cells": {start_pos} - self.death_memory["pits"],
            "confirmed_pits": set(self.death_memory["pits"]),
            "confirmed_wumpus": self.death_memory["wumpus"],
            "possible_pits": set(self.death_memory["pits"]),
            "possible_wumpus": {self.death_memory["wumpus"]} if self.death_memory["wumpus"] else set(),
            "pit_free": {start_pos} - self.death_memory["pits"],
            "wumpus_free": {start_pos} if self.death_memory["wumpus"] != start_pos else set(),
        }

        # Path queue & thoughts
        self.last_action = "INITIALIZED"
        if self.has_death_memory():
            summary = self.get_memory_summary()
            self.thought_process = f"🧠 Replay initialized with episodic memory ({summary})."
        else:
            self.thought_process = "Agent initialized at safe start position."

    def reset(self, start_pos=(3, 0), keep_memory=False):
        """
        Resets Agent state for a new round.
        If keep_memory is True, retains death_memory learned from previous failures on this map.
        """
        retained_mem = self.death_memory if keep_memory else None
        self.__init__(start_pos, self.size, death_memory=retained_mem)

    def record_death(self, reason, fatal_cell):
        """
        Registers fatal outcome into episodic memory so the agent avoids repeating it upon replay.
        """
        if reason == "FALL_IN_PIT":
            self.death_memory["pits"].add(fatal_cell)
        elif reason == "EATEN_BY_WUMPUS":
            self.death_memory["wumpus"] = fatal_cell

    def clear_death_memory(self):
        """Wipes cross-episode memory when switching to a completely new map."""
        self.death_memory = {"pits": set(), "wumpus": None}

    def has_death_memory(self):
        """Returns True if agent has learned any fatal hazards from previous runs."""
        return bool(self.death_memory["pits"] or self.death_memory["wumpus"] is not None)

    def get_memory_summary(self):
        """Returns human-readable summary of recalled hazards."""
        items = []
        if self.death_memory["pits"]:
            pits_str = ", ".join(str(p) for p in sorted(list(self.death_memory["pits"])))
            items.append(f"Pit(s) at {pits_str}")
        if self.death_memory["wumpus"]:
            items.append(f"Wumpus at {self.death_memory['wumpus']}")
        return "; ".join(items) if items else "No fatal history"

    def perceive(self, current_percepts):
        """
        PERCEPTION Stage:
        Receives environmental signals at current cell and records to memory.
        """
        self.visited.add(self.position)
        self.percepts_history[self.position] = set(current_percepts)

    def reason(self, is_wumpus_alive=True):
        """
        REASONING Stage:
        Applies logic rules and cross-episode death memory to update the Knowledge Base.
        """
        self.knowledge = deduce_knowledge(
            self.size,
            self.visited,
            self.percepts_history,
            is_wumpus_alive,
            death_memory=self.death_memory,
        )

    def find_shortest_path(self, target_cells, allowed_cells):
        """
        Finds the shortest path (BFS) from current position to any cell in `target_cells`,
        traversing only through `allowed_cells`.
        """
        if not target_cells:
            return None

        queue = deque([(self.position, [self.position])])
        visited_in_search = {self.position}

        while queue:
            current, path = queue.popleft()

            if current in target_cells and current != self.position:
                return path[1:]  # Exclude start pos, return next steps

            for neighbor in get_adjacent_cells(current, self.size):
                if neighbor in allowed_cells and neighbor not in visited_in_search:
                    visited_in_search.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def get_shoot_direction(self, target_pos):
        """Determines shooting direction from current position if aligned along row/col."""
        r, c = self.position
        tr, tc = target_pos
        if r == tr:
            return "RIGHT" if tc > c else "LEFT"
        elif c == tc:
            return "DOWN" if tr > r else "UP"
        return None

    def decide_next_action(self, is_wumpus_alive=True):
        """
        DECISION Stage:
        Selects the optimal action based on current knowledge and goals.
        """
        current_percepts = self.percepts_history.get(self.position, set())

        # 1. If Glitter observed -> GRAB GOLD
        if "glitter" in current_percepts and not self.has_gold:
            self.last_action = "GRAB_GOLD"
            self.thought_process = "✨ Glitter detected! Grabbing the Gold!"
            return {"type": "GRAB"}

        # 2. If Gold already acquired -> RETREAT TO START CELL
        if self.has_gold:
            if self.position == self.start_pos:
                self.last_action = "CLIMB_OUT"
                self.thought_process = "🏆 Gold brought back to start cell. Climbing out of the cave!"
                return {"type": "CLIMB"}

            # Find safe path back to start
            path_home = self.find_shortest_path({self.start_pos}, self.knowledge["safe_cells"])
            if path_home:
                next_cell = path_home[0]
                self.last_action = f"RETURN_TO_{next_cell}"
                self.thought_process = f"Carrying Gold safely back towards start via {next_cell}."
                return {"type": "MOVE", "to": next_cell}

        # 3. If there are UNVISITED SAFE CELLS -> Explore closest
        unvisited_safe = self.knowledge["safe_cells"] - self.visited
        if unvisited_safe:
            path = self.find_shortest_path(unvisited_safe, self.knowledge["safe_cells"])
            if path:
                next_cell = path[0]
                self.last_action = f"EXPLORE_SAFE_{next_cell}"
                self.thought_process = f"Found safe unvisited cell {path[-1]}. Moving to {next_cell}."
                return {"type": "MOVE", "to": next_cell}

        # 4. If Wumpus location is CONFIRMED and arrow available -> SHOOT
        confirmed_wumpus = self.knowledge.get("confirmed_wumpus")
        if self.has_arrow and confirmed_wumpus and is_wumpus_alive:
            shoot_dir = self.get_shoot_direction(confirmed_wumpus)
            if shoot_dir:
                self.last_action = f"SHOOT_{shoot_dir}"
                self.thought_process = f"🎯 Locked onto Wumpus at {confirmed_wumpus}! Shooting {shoot_dir}!"
                return {"type": "SHOOT", "direction": shoot_dir}
            else:
                # Navigate to a safe cell aligned with Wumpus
                aligned_safe = [
                    pos for pos in self.knowledge["safe_cells"]
                    if (pos[0] == confirmed_wumpus[0] or pos[1] == confirmed_wumpus[1])
                ]
                align_path = self.find_shortest_path(aligned_safe, self.knowledge["safe_cells"])
                if align_path:
                    next_cell = align_path[0]
                    self.last_action = f"ALIGN_FOR_SHOT_{next_cell}"
                    self.thought_process = f"Repositioning to {next_cell} to align shot against Wumpus."
                    return {"type": "MOVE", "to": next_cell}

        # 5. If NO 100% safe cells remain: Risk Evaluation
        candidates = []
        for nb in get_adjacent_cells(self.position, self.size):
            if nb not in self.visited:
                risk = calculate_cell_risk(nb, self.knowledge)
                if risk < 10:  # Not a confirmed hazard
                    candidates.append((risk, nb))

        if candidates:
            # Pick neighbor with lowest risk
            candidates.sort(key=lambda x: x[0])
            lowest_risk, chosen_cell = candidates[0]

            # Detect if episodic memory successfully diverted agent away from a fatal hazard
            avoided_hazards = [
                nb for nb in get_adjacent_cells(self.position, self.size)
                if nb in self.death_memory["pits"] or nb == self.death_memory["wumpus"]
            ]
            avoidance_note = ""
            if avoided_hazards:
                avoidance_note = f" 🧠 [Memory] Avoided fatal cell(s) {avoided_hazards}!"

            self.last_action = f"RISKY_MOVE_{chosen_cell}"
            self.thought_process = (
                f"⚠️ No safe cells left. Taking calculated risk into {chosen_cell} "
                f"(Risk: {lowest_risk}).{avoidance_note}"
            )
            return {"type": "MOVE", "to": chosen_cell}

        # 6. Deadlock or too perilous -> Retreat safely
        if self.position == self.start_pos:
            self.last_action = "CLIMB_OUT"
            self.thought_process = "🛑 Environment is too dangerous. Retreating safely without gold."
            return {"type": "CLIMB"}

        path_home = self.find_shortest_path({self.start_pos}, self.knowledge["safe_cells"])
        if path_home:
            next_cell = path_home[0]
            self.last_action = f"RETREAT_TO_{next_cell}"
            self.thought_process = f"Blocked, retreating to start position via {next_cell}."
            return {"type": "MOVE", "to": next_cell}

        return {"type": "PASS"}