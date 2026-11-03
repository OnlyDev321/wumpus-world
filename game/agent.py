from collections import deque
from game.rules import deduce_knowledge, calculate_cell_risk
from game.i18n import T, Join


class Agent:
    """
    AI Agent implementing the complete loop:
    Perception -> Memory -> Reasoning -> Decision Making -> Action.
    Enhanced with Episodic Memory to retain fatal failure causes across replays.

    The agent knows the dungeon layout (rooms, doors, entrance and exit) but not where
    the hazards and the gold are. It only reads layout data from `layout` (the World).
    """

    GOLD_DETOUR = 4  # max extra steps to line up a sure shot while carrying the gold

    def __init__(self, layout, death_memory=None):
        self.layout = layout
        self.start_pos = layout.start_position
        self.exit_pos = layout.exit_position
        self.position = self.start_pos
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
        start = self.start_pos
        self.knowledge = {
            "safe_cells": {start} - self.death_memory["pits"],
            "confirmed_pits": set(self.death_memory["pits"]),
            "confirmed_wumpus": self.death_memory["wumpus"],
            "possible_pits": set(self.death_memory["pits"]),
            "possible_wumpus": {self.death_memory["wumpus"]} if self.death_memory["wumpus"] else set(),
            "pit_free": {start} - self.death_memory["pits"],
            "wumpus_free": {start} if self.death_memory["wumpus"] != start else set(),
        }

        self.last_action = "INITIALIZED"
        if self.has_death_memory():
            self.thought_process = T("th.replay", summary=self.get_memory_summary())
        else:
            self.thought_process = T("th.start")

    def neighbors(self, pos):
        return self.layout.get_adjacent(pos)

    def name(self, pos):
        return self.layout.label(pos)

    def reset(self, keep_memory=False):
        """
        Resets Agent state for a new round (reads the current layout again).
        If keep_memory is True, retains death_memory learned from previous failures on this map.
        """
        retained_mem = self.death_memory if keep_memory else None
        self.__init__(self.layout, death_memory=retained_mem)

    def record_death(self, reason, fatal_cell):
        """Registers fatal outcome into episodic memory so the agent avoids repeating it upon replay."""
        if reason == "FALL_IN_PIT":
            self.death_memory["pits"].add(fatal_cell)
        elif reason == "EATEN_BY_WUMPUS":
            self.death_memory["wumpus"] = fatal_cell

    def clear_death_memory(self):
        """Wipes cross-episode memory when switching to a completely new map."""
        self.death_memory = {"pits": set(), "wumpus": None}

    def has_death_memory(self):
        return bool(self.death_memory["pits"] or self.death_memory["wumpus"] is not None)

    def get_memory_summary(self):
        items = []
        if self.death_memory["pits"]:
            items.append(T("mem.pit", cells=", ".join(self.name(p) for p in sorted(self.death_memory["pits"]))))
        if self.death_memory["wumpus"]:
            items.append(T("mem.wumpus", cell=self.name(self.death_memory["wumpus"])))
        return Join(items, "; ") if items else T("mem.none")

    def perceive(self, current_percepts):
        """PERCEPTION: records the signals at the current cell."""
        self.visited.add(self.position)
        self.percepts_history[self.position] = set(current_percepts)

    def reason(self, is_wumpus_alive=True):
        """REASONING: applies logic rules and death memory to update the Knowledge Base."""
        self.knowledge = deduce_knowledge(
            self.layout.cells,
            self.neighbors,
            self.visited,
            self.percepts_history,
            is_wumpus_alive,
            death_memory=self.death_memory,
        )

    def find_shortest_path(self, target_cells, allowed_cells):
        """
        BFS from the current position to any cell in `target_cells`,
        stepping only through `allowed_cells`. Returns the steps after the current cell.
        """
        if not target_cells:
            return None

        queue = deque([(self.position, [self.position])])
        seen = {self.position}
        while queue:
            current, path = queue.popleft()
            if current in target_cells and current != self.position:
                return path[1:]
            for nb in self.neighbors(current):
                if nb in allowed_cells and nb not in seen:
                    seen.add(nb)
                    queue.append((nb, path + [nb]))
        return None

    def get_shoot_direction(self, target_pos):
        """Shooting direction if the target is in the same room and on the same row/column."""
        if self.layout.room_of(target_pos) != self.layout.room_of(self.position):
            return None
        r, c = self.position
        tr, tc = target_pos
        if r == tr:
            return "RIGHT" if tc > c else "LEFT"
        if c == tc:
            return "DOWN" if tr > r else "UP"
        return None

    def _plan_shot(self, safe, max_steps=None):
        """
        Returns a SHOOT action, a MOVE towards a firing spot, or None.

        A shot is taken only when it cannot miss: the Wumpus is confirmed, or every cell
        it could be in lies on one straight line inside one room, all on the same side
        of a safe firing spot (the arrow flies through all of them).
        """
        if not self.has_arrow:
            return None
        kb = self.knowledge
        targets = {kb["confirmed_wumpus"]} if kb.get("confirmed_wumpus") else set(kb["possible_wumpus"])
        if not targets or len(targets) > 3:
            return None
        rooms = {self.layout.room_of(t) for t in targets}
        if len(rooms) != 1:
            return None
        room = rooms.pop()

        spots = {}
        for pos in safe | {self.position}:
            if self.layout.room_of(pos) != room or pos in targets:
                continue
            r, c = pos
            if all(t[0] == r for t in targets):
                if all(t[1] > c for t in targets):
                    spots[pos] = "RIGHT"
                elif all(t[1] < c for t in targets):
                    spots[pos] = "LEFT"
            if pos not in spots and all(t[1] == c for t in targets):
                if all(t[0] > r for t in targets):
                    spots[pos] = "DOWN"
                elif all(t[0] < r for t in targets):
                    spots[pos] = "UP"
        if not spots:
            return None

        where = ", ".join(self.name(t) for t in sorted(targets))
        if self.position in spots:
            direction = spots[self.position]
            self.last_action = f"SHOOT_{direction}"
            key = "th.shoot_sure" if len(targets) == 1 else "th.shoot_line"
            self.thought_process = T(key, where=where, dir=T(f"dir.{direction}"), bonus=500)
            return {"type": "SHOOT", "direction": direction}

        path = self.find_shortest_path(set(spots), safe)
        if path and (max_steps is None or len(path) <= max_steps):
            self.last_action = f"ALIGN_FOR_SHOT_{path[0]}"
            self.thought_process = T("th.align", where=where, cell=self.name(path[0]))
            return {"type": "MOVE", "to": path[0]}
        return None

    def _go_to_exit(self, reason_text):
        """Climb out if standing on the exit, otherwise step along a safe path to it."""
        if self.position == self.exit_pos:
            self.last_action = "CLIMB_OUT"
            self.thought_process = reason_text
            return {"type": "CLIMB"}
        path = self.find_shortest_path({self.exit_pos}, self.knowledge["safe_cells"] | {self.exit_pos})
        if path:
            self.last_action = f"TO_EXIT_{path[0]}"
            self.thought_process = T("th.to_exit", exit=self.name(self.exit_pos), cell=self.name(path[0]))
            return {"type": "MOVE", "to": path[0]}
        return None

    def decide_next_action(self, is_wumpus_alive=True):
        """DECISION: selects the next action from current knowledge and goals."""
        current_percepts = self.percepts_history.get(self.position, set())
        # The exit ends the game as soon as it is stepped on, so it is kept out of
        # exploration and only used when the agent decides to leave (_go_to_exit).
        safe = self.knowledge["safe_cells"] - {self.exit_pos}

        # 1. Glitter -> grab the gold
        if "glitter" in current_percepts and not self.has_gold:
            self.last_action = "GRAB_GOLD"
            self.thought_process = T("th.grab")
            return {"type": "GRAB"}

        # 2. Gold in hand -> go to the exit (not back to the entrance).
        #    A sure shot only a few steps away is still worth the +500 detour.
        if self.has_gold:
            action = self._plan_shot(safe, max_steps=self.GOLD_DETOUR) if is_wumpus_alive else None
            if action:
                return action
            action = self._go_to_exit(T("th.leave_gold"))
            if action:
                return action

        # 3. Explore the closest safe unvisited cell
        unvisited_safe = safe - self.visited
        if unvisited_safe:
            path = self.find_shortest_path(unvisited_safe, safe)
            if path:
                self.last_action = f"EXPLORE_SAFE_{path[0]}"
                self.thought_process = T("th.explore", target=self.name(path[-1]), cell=self.name(path[0]))
                return {"type": "MOVE", "to": path[0]}

        # 4. Safe exploration is done: hunt the Wumpus for +500 if a shot cannot miss
        if is_wumpus_alive:
            action = self._plan_shot(safe)
            if action:
                return action

        # 5. No safe cells left: pick the lowest-risk cell on the whole explored frontier
        frontier_candidates = []
        for v_cell in self.visited:
            for nb in self.neighbors(v_cell):
                if nb in self.visited or nb == self.exit_pos:
                    continue
                risk = calculate_cell_risk(nb, self.knowledge)
                if risk >= 10:  # confirmed hazard
                    continue
                if v_cell == self.position:
                    path_to_bridge, dist = [], 1
                else:
                    path_to_bridge = self.find_shortest_path({v_cell}, safe)
                    if path_to_bridge is None:
                        continue
                    dist = len(path_to_bridge) + 1
                frontier_candidates.append((risk, dist, nb, v_cell, path_to_bridge))

        if frontier_candidates:
            frontier_candidates.sort(key=lambda item: (item[0], item[1]))
            lowest_risk, dist, target, bridge, path_to_bridge = frontier_candidates[0]

            if bridge == self.position:
                avoided = [
                    nb for nb in self.neighbors(self.position)
                    if nb in self.death_memory["pits"] or nb == self.death_memory["wumpus"]
                ]
                note = T("th.avoided", cells=", ".join(self.name(a) for a in avoided)) if avoided else ""
                self.last_action = f"RISKY_MOVE_{target}"
                self.thought_process = Join(
                    [T("th.risky", cell=self.name(target), risk=f"{lowest_risk:.0%}"), note], "")
                return {"type": "MOVE", "to": target}

            self.last_action = f"NAVIGATE_TO_FRONTIER_{path_to_bridge[0]}"
            self.thought_process = T("th.frontier", cell=self.name(path_to_bridge[0]), target=self.name(target),
                                     risk=f"{lowest_risk:.0%}", dist=dist)
            return {"type": "MOVE", "to": path_to_bridge[0]}

        # 6. Nothing left to explore: leave through the exit without the gold
        action = self._go_to_exit(T("th.leave_nogold"))
        if action:
            return action

        self.last_action = "TRAPPED"
        self.thought_process = T("th.trapped")
        return {"type": "PASS"}
