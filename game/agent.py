from heapq import heappop, heappush
from itertools import count

from game.scoring import MOVE_COST, SHOT_COST, DEATH_COST
from game.rules import deduce_knowledge, calculate_cell_risk
from game.i18n import T, Join


class Agent:
    """
    AI Agent implementing the complete loop:
    Perception -> Memory -> Reasoning -> Decision Making -> Action.
    Enhanced with Episodic Memory to retain fatal failure causes across replays.

    The agent knows only the entrance and that rooms are square (room_size x room_size).
    It does not know how many rooms there are or where the doors are: a room becomes
    known when the agent enters it, and a door (with the cell it leads to) is remembered
    once the agent has walked through it. The exit is learned only from a percept on its
    cell; hazards and gold are also discovered through perception.
    """

    ALLOW_RISK = True

    def __init__(self, layout, death_memory=None):
        # Read only for the entrance, the room size and cell names in messages.
        # Doors, rooms and hazards are never read from it.
        self._map = layout
        self.room_size = layout.room_size
        self.start_pos = layout.start_position
        self.known_doors = {}  # door cell -> cell on the other side, learned by walking through
        self.known_cells = set(self._room_cells(self.start_pos))
        self.exit_pos = None
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
        self.missed_shots = set()
        start = self.start_pos
        self.knowledge = {
            "safe_cells": {start} - self.death_memory["pits"],
            "confirmed_pits": set(self.death_memory["pits"]),
            "confirmed_wumpus": self.death_memory["wumpus"],
            "possible_pits": set(self.death_memory["pits"]),
            "possible_wumpus": {self.death_memory["wumpus"]} if self.death_memory["wumpus"] else set(),
            "pit_free": {start} - self.death_memory["pits"],
            "wumpus_free": {start} if self.death_memory["wumpus"] != start else set(),
            "wumpus_localized": self.death_memory["wumpus"] is not None,
        }

        self.last_action = "INITIALIZED"
        if self.has_death_memory():
            self.thought_process = T("th.replay", summary=self.get_memory_summary())
        else:
            self.thought_process = T("th.start")

    def _room(self, pos):
        """Room block of a cell. Rooms are square, so this follows from coordinates alone."""
        return (pos[0] // self.room_size, pos[1] // self.room_size)

    def _room_cells(self, pos):
        S = self.room_size
        top, left = pos[0] // S * S, pos[1] // S * S
        return [(top + r, left + c) for r in range(S) for c in range(S)]

    def neighbors(self, pos):
        """Cells one step away as far as the agent knows: same room, plus doors it has used."""
        r, c = pos
        room = self._room(pos)
        result = [nb for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)) if self._room(nb) == room]
        if pos in self.known_doors:
            result.append(self.known_doors[pos])
        return result

    def learn_door(self, door, landing):
        """Called by the game after the agent passes through `door` and lands on `landing`."""
        self.known_doors[door] = landing
        self.known_doors[landing] = door
        self.known_cells.update(self._room_cells(landing))

    def name(self, pos):
        return self._map.label(pos)

    def reset(self, keep_memory=False):
        """
        Resets Agent state for a new round (reads the entrance and room size again).
        If keep_memory is True, retains death_memory learned from previous failures on this map.
        Rooms and doors are forgotten and must be discovered again.
        """
        retained_mem = self.death_memory if keep_memory else None
        self.__init__(self._map, death_memory=retained_mem)

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
        if "exit" in current_percepts:
            self.exit_pos = self.position

    def record_missed_shot(self, cells):
        """Records cells traversed by an arrow that missed, guaranteeing they contain no Wumpus."""
        self.missed_shots.update(cells)

    def reason(self, is_wumpus_alive=True):
        """REASONING: applies logic rules and death memory to update the Knowledge Base."""
        self.knowledge = deduce_knowledge(
            self.known_cells,
            self.neighbors,
            self.visited,
            self.percepts_history,
            is_wumpus_alive,
            death_memory=self.death_memory,
            missed_shots=self.missed_shots,
        )

    def _route_to(self, goals, safe, allow_shot=False):
        """Cheapest known-safe action sequence, including positioning and one sure shot.

        Search state includes whether the arrow has been fired. After a guaranteed
        kill, only pit-free cells become traversable. No hidden hazards are read.
        Entering a door the agent has already used teleports in the same MOVE, just as
        GameManager executes it; unknown doors look like ordinary cells.
        Equal-cost routes prefer preserving the arrow.
        """
        goals = set(goals)
        if not goals:
            return None
        safe = set(safe) | {self.position}
        after_shot = (safe | self.knowledge["pit_free"]) - self.knowledge["confirmed_pits"]
        # Without a stench (or a remembered death) the Wumpus may be in a room not seen yet,
        # so no shot can be guaranteed.
        if self.knowledge["confirmed_wumpus"] is not None:
            targets = {self.knowledge["confirmed_wumpus"]}
        elif self.knowledge.get("wumpus_localized"):
            targets = set(self.knowledge["possible_wumpus"])
        else:
            targets = set()
        can_shoot = allow_shot and self.has_arrow and bool(targets)
        serial = count()
        queue = [(0, 0, next(serial), self.position, [])]
        best = {(self.position, 0): 0}
        while queue:
            cost, shots, _, pos, actions = heappop(queue)
            if cost != best.get((pos, shots)):
                continue
            if pos in goals:
                return cost, actions, pos
            allowed = after_shot if shots else safe
            options = []
            for target in self.neighbors(pos):
                if target not in allowed:
                    continue
                landing = target
                if target in self.known_doors and self._room(target) == self._room(pos):
                    # Stepping onto a known door from its own room carries us through it.
                    landing = self.known_doors[target]
                options.append((MOVE_COST, shots, landing, {"type": "MOVE", "to": target}))
            if can_shoot and not shots:
                direction = self._sure_shot_direction(pos, targets)
                if direction:
                    options.append((SHOT_COST, 1, pos, {"type": "SHOOT", "direction": direction}))
            for extra, next_shots, landing, action in options:
                next_cost = cost + extra
                state = (landing, next_shots)
                if next_cost < best.get(state, float("inf")):
                    best[state] = next_cost
                    heappush(queue, (next_cost, next_shots, next(serial), landing, actions + [action]))
        return None

    def find_shortest_path(self, target_cells, allowed_cells):
        """Fewest MOVE actions, counting automatic door crossings correctly."""
        route = self._route_to(set(target_cells) - {self.position}, allowed_cells)
        return [action["to"] for action in route[1]] if route else None

    def _sure_shot_direction(self, pos, targets):
        if any(self._room(t) != self._room(pos) for t in targets):
            return None
        r, c = pos
        if all(t[0] == r for t in targets):
            if all(t[1] > c for t in targets):
                return "RIGHT"
            if all(t[1] < c for t in targets):
                return "LEFT"
        if all(t[1] == c for t in targets):
            if all(t[0] > r for t in targets):
                return "DOWN"
            if all(t[0] < r for t in targets):
                return "UP"
        return None

    def get_shoot_direction(self, target_pos):
        """Shooting direction if the target is in the same room and on the same row/column."""
        if self._room(target_pos) != self._room(self.position):
            return None
        r, c = self.position
        tr, tc = target_pos
        if r == tr:
            return "RIGHT" if tc > c else "LEFT"
        if c == tc:
            return "DOWN" if tr > r else "UP"
        return None

    def _plan_shot(self, safe, goals):
        """Plan a kill only when it opens a pit-free route to a useful goal."""
        route = self._route_to(goals, safe, allow_shot=True)
        if route and any(action["type"] == "SHOOT" for action in route[1]):
            return route
        return None

    def _follow_shot_route(self, route):
        cost, actions, goal = route
        action = actions[0]
        if action["type"] == "SHOOT":
            self.last_action = f"SHOOT_{action['direction']}"
            self.thought_process = T("th.shoot_needed", cell=self.name(goal), cost=cost,
                                     dir=T(f"dir.{action['direction']}"))
        else:
            self.last_action = f"ALIGN_FOR_SHOT_{action['to']}"
            self.thought_process = T("th.align_needed", cell=self.name(action["to"]),
                                     goal=self.name(goal), cost=cost)
        return action

    def _go_to_exit(self, reason_text, allow_shot=False):
        """Minimize total point cost to exit, preferring no shot on a tie."""
        if self.exit_pos is None:
            return None
        if self.position == self.exit_pos:
            self.last_action = "CLIMB_OUT"
            self.thought_process = reason_text
            return {"type": "CLIMB"}
        route = self._route_to({self.exit_pos}, self.knowledge["safe_cells"] | {self.exit_pos},
                               allow_shot=allow_shot)
        if route:
            if any(action["type"] == "SHOOT" for action in route[1]):
                return self._follow_shot_route(route)
            action = route[1][0]
            self.last_action = f"TO_EXIT_{action['to']}"
            self.thought_process = T("th.to_exit", exit=self.name(self.exit_pos), cell=self.name(action["to"]))
            return action
        return None

    def decide_next_action(self, is_wumpus_alive=True):
        """DECISION: selects the next action from current knowledge and goals."""
        current_percepts = self.percepts_history.get(self.position, set())
        # Without gold, the exit is an ordinary cell that can be explored or crossed.
        safe = self.knowledge["safe_cells"]

        # 1. Glitter -> grab the gold
        if "glitter" in current_percepts and not self.has_gold:
            self.last_action = "GRAB_GOLD"
            self.thought_process = T("th.grab")
            return {"type": "GRAB"}

        # 2. Gold in hand -> go to the exit (not back to the entrance).
        #    Compare walking versus a guaranteed kill, including all point costs.
        if self.has_gold:
            action = self._go_to_exit(T("th.leave_gold"), allow_shot=is_wumpus_alive)
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

        # 4. No reachable safe exploration: compare opening a useful safe route
        #    with the expected death penalty of taking a frontier risk.
        shot_route = (self._plan_shot(safe, self.knowledge["pit_free"] - self.visited)
                      if is_wumpus_alive and (not self.has_gold or self.exit_pos is None) else None)

        # 5. No safe cells left: pick the lowest-risk cell on the whole explored frontier
        frontier_candidates = []
        for v_cell in (self.visited if self.ALLOW_RISK else ()):
            for nb in self.neighbors(v_cell):
                if nb in self.visited:
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
            frontier_candidates.sort(key=lambda item: (item[0] * DEATH_COST + item[1] * MOVE_COST,
                                                        item[0], item[1], item[2]))
            risk, distance = frontier_candidates[0][:2]
            if shot_route and shot_route[0] < risk * DEATH_COST + distance * MOVE_COST:
                return self._follow_shot_route(shot_route)
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

        if shot_route:
            return self._follow_shot_route(shot_route)

        # 6. Deadlock encountered: try to retreat safely to known exit instead of giving up
        if self.exit_pos is not None:
            if self.position == self.exit_pos:
                self.last_action = "CLIMB_OUT"
                self.thought_process = T("th.leave_deadlock")
                return {"type": "CLIMB"}
            retreat_path = self.find_shortest_path({self.exit_pos}, safe | {self.exit_pos})
            if retreat_path:
                next_cell = retreat_path[0]
                self.last_action = f"RETREAT_TO_{next_cell}"
                self.thought_process = T("th.retreat_exit", exit=self.name(self.exit_pos), cell=self.name(next_cell))
                return {"type": "MOVE", "to": next_cell}

        # 7. No way to continue the search or reach the goal: report failure.
        self.last_action = "TRAPPED"
        self.thought_process = T("th.trapped")
        return {"type": "PASS"}
