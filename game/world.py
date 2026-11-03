import random
from collections import deque

DIRECTIONS = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


class World:
    """
    Wumpus World dungeon made of square rooms (4x4 by default).

    All cells use global (row, col) coordinates on one big grid. Room walls block
    movement, percepts and arrows, except at doors that link two neighbouring rooms
    (doors work both ways). The agent enters through the entrance in Room 1 and can
    leave the dungeon only through a separate exit in the farthest room.
    """

    MIN_ROOMS = 1
    MAX_ROOMS = 6

    def __init__(self, num_rooms=1, room_size=4, classic=False, pit_prob=0.15):
        self.room_size = room_size
        self.size = room_size
        self.pit_prob = pit_prob
        if classic:
            self.generate_classic_world()
        else:
            self.generate_random_world(num_rooms)

    # ------------------------------------------------------------------
    # Layout (rooms, walls, doors)
    # ------------------------------------------------------------------
    def _build_layout(self, room_origins, door_pairs):
        """Builds cells and the movement graph from room grid positions and door cell pairs."""
        S = self.room_size
        self.rooms = list(room_origins)
        self.num_rooms = len(self.rooms)
        self._room_by_origin = {origin: i for i, origin in enumerate(self.rooms)}
        self.room_rows = max(ry for ry, _ in self.rooms) + 1
        self.room_cols = max(rx for _, rx in self.rooms) + 1
        self.rows = self.room_rows * S
        self.cols = self.room_cols * S

        self.cells = {
            (ry * S + r, rx * S + c)
            for ry, rx in self.rooms
            for r in range(S)
            for c in range(S)
        }
        self.doors = [tuple(pair) for pair in door_pairs]
        self.door_cells = {cell for pair in self.doors for cell in pair}

        self.adj = {cell: [] for cell in self.cells}
        for cell in self.cells:
            for dr, dc in DIRECTIONS.values():
                nb = (cell[0] + dr, cell[1] + dc)
                if nb in self.cells and self.room_of(nb) == self.room_of(cell):
                    self.adj[cell].append(nb)
        for a, b in self.doors:
            self.adj[a].append(b)
            self.adj[b].append(a)

    def _random_layout(self, num_rooms):
        """Grows a connected set of rooms, then adds a few extra doors to form loops."""
        S = self.room_size
        origins = [(0, 0)]
        links = []
        while len(origins) < num_rooms:
            base = random.choice(origins)
            dr, dc = random.choice(list(DIRECTIONS.values()))
            new = (base[0] + dr, base[1] + dc)
            if new not in origins:
                origins.append(new)
                links.append((base, new))

        linked = {frozenset(link) for link in links}
        for a in origins:
            for dr, dc in ((0, 1), (1, 0)):
                b = (a[0] + dr, a[1] + dc)
                if b in origins and frozenset((a, b)) not in linked and random.random() < 0.35:
                    links.append((a, b))

        min_r = min(r for r, _ in origins)
        min_c = min(c for _, c in origins)
        shift = lambda o: (o[0] - min_r, o[1] - min_c)
        origins = [shift(o) for o in origins]
        links = [(shift(a), shift(b)) for a, b in links]

        def door_cells(a, b, k):
            if a[0] == b[0]:
                left, right = sorted((a, b), key=lambda o: o[1])
                return (left[0] * S + k, left[1] * S + S - 1), (right[0] * S + k, right[1] * S)
            top, bottom = sorted((a, b), key=lambda o: o[0])
            return (top[0] * S + S - 1, top[1] * S + k), (bottom[0] * S, bottom[1] * S + k)

        # Every door gets its own cells, and never the entrance cell (bottom-left of Room 1)
        used = {(origins[0][0] * S + S - 1, origins[0][1] * S)}
        doors = []
        for a, b in links:
            options = [k for k in range(S) if not used & set(door_cells(a, b, k))] or list(range(S))
            pair = door_cells(a, b, random.choice(options))
            used.update(pair)
            doors.append(pair)
        return origins, doors

    def room_of(self, pos):
        """Index of the room containing `pos` (0-based)."""
        S = self.room_size
        return self._room_by_origin[(pos[0] // S, pos[1] // S)]

    def room_cells(self, room_idx):
        """All cells of a room, row by row."""
        S = self.room_size
        ry, rx = self.rooms[room_idx]
        return [(ry * S + r, rx * S + c) for r in range(S) for c in range(S)]

    def local(self, pos):
        """Position inside its room."""
        return (pos[0] % self.room_size, pos[1] % self.room_size)

    def label(self, pos):
        """Human-readable cell name, e.g. 'R2 (1,3)'."""
        lr, lc = self.local(pos)
        if self.num_rooms > 1:
            return f"R{self.room_of(pos) + 1} ({lr},{lc})"
        return f"({lr},{lc})"

    def door_partner(self, cell):
        """The door cell on the other side of the wall, or None if `cell` is not a door."""
        for a, b in self.doors:
            if cell == a:
                return b
            if cell == b:
                return a
        return None

    def get_adjacent(self, pos):
        """Cells reachable in one step from `pos` (same room, or through a door)."""
        return self.adj[pos]

    def _room_distances(self, start_room):
        """BFS distances between rooms over doors."""
        dist = {start_room: 0}
        queue = deque([start_room])
        while queue:
            room = queue.popleft()
            for a, b in self.doors:
                ra, rb = self.room_of(a), self.room_of(b)
                for here, there in ((ra, rb), (rb, ra)):
                    if here == room and there not in dist:
                        dist[there] = dist[room] + 1
                        queue.append(there)
        return dist

    # ------------------------------------------------------------------
    # Map generation
    # ------------------------------------------------------------------
    def generate_classic_world(self):
        """The original hand-made 4x4 map (one room). Gold is reachable only by killing the Wumpus."""
        self._build_layout([(0, 0)], [])
        self.start_position = (3, 0)
        self.exit_position = (0, 3)
        self.pits = {(0, 2), (2, 2), (3, 3)}
        self.wumpus = (1, 1)
        self.gold = (1, 2)
        self._save_initial_state()

    def generate_random_world(self, num_rooms=None):
        """
        Generates a random dungeon where:
        - the entrance, its neighbours, the exit, door cells and their neighbours have no hazards,
        - every room has at least one pit,
        - the gold and the exit can be reached from the entrance without passing a pit or the Wumpus.
        """
        if num_rooms is None:
            num_rooms = getattr(self, "num_rooms", 1)
        num_rooms = max(self.MIN_ROOMS, min(self.MAX_ROOMS, num_rooms))
        S = self.room_size

        origins, doors = self._random_layout(num_rooms)
        self._build_layout(origins, doors)

        ry, rx = self.rooms[0]
        self.start_position = (ry * S + S - 1, rx * S)

        # Exit goes into the farthest room, in the corner farthest from the entrance
        dist = self._room_distances(0)
        far = max(dist.values())
        exit_room = random.choice([room for room, d in dist.items() if d == far])
        sr, sc = self.start_position
        corners = [
            cell for cell in self.room_cells(exit_room)
            if self.local(cell)[0] in (0, S - 1) and self.local(cell)[1] in (0, S - 1)
            and cell not in self.door_cells and cell != self.start_position
        ] or [
            cell for cell in self.room_cells(exit_room)
            if cell not in self.door_cells and cell != self.start_position
        ]
        self.exit_position = max(corners, key=lambda cell: abs(cell[0] - sr) + abs(cell[1] - sc))

        # Door cells and their neighbours stay clear, so walking into a new room is never a blind gamble
        door_zone = {nb for door in self.door_cells for nb in self.adj[door]} | self.door_cells
        protected = {self.start_position, self.exit_position, *self.adj[self.start_position], *door_zone}
        candidates = [cell for cell in self.cells if cell not in protected]
        gold_candidates = [cell for cell in candidates if num_rooms == 1 or self.room_of(cell) != 0] or candidates

        while True:
            self.wumpus = random.choice(candidates)
            self.gold = random.choice([cell for cell in gold_candidates if cell != self.wumpus])
            self.pits = {
                cell for cell in candidates
                if cell not in (self.wumpus, self.gold) and random.random() < self.pit_prob
            }
            # Every room gets at least one pit, so no room is left empty
            for room in range(num_rooms):
                free = [c for c in candidates if self.room_of(c) == room and c not in (self.wumpus, self.gold)]
                if free and not self.pits.intersection(free):
                    self.pits.add(random.choice(free))
            if self._safe_path_exists(self.start_position, self.gold) and \
                    self._safe_path_exists(self.gold, self.exit_position):
                break

        self._save_initial_state()

    def _safe_path_exists(self, src, dst):
        """BFS over cells that are neither pits nor the Wumpus."""
        seen = {src}
        queue = [src]
        while queue:
            pos = queue.pop()
            if pos == dst:
                return True
            for nb in self.adj[pos]:
                if nb not in seen and nb not in self.pits and nb != self.wumpus:
                    seen.add(nb)
                    queue.append(nb)
        return False

    def _save_initial_state(self):
        self.initial_pits = set(self.pits)
        self.initial_wumpus = self.wumpus
        self.initial_gold = self.gold
        self.start_pos = self.start_position
        self.reset_world()

    def reset_world(self):
        """Restores the current map to its initial layout."""
        self.agent_position = self.start_position
        self.pits = set(self.initial_pits)
        self.wumpus = self.initial_wumpus
        self.gold = self.initial_gold
        self.is_wumpus_alive = True
        self.gold_taken = False
        self.last_action_screamed = False

    # ------------------------------------------------------------------
    # Percepts & actions
    # ------------------------------------------------------------------
    def get_percepts(self, pos):
        """
        Returns the set of percepts at cell pos:
        - breeze: adjacent to a Pit
        - stench: adjacent to Wumpus (when alive)
        - glitter: current cell contains Gold
        - scream: Wumpus killed on the previous action
        """
        percepts = set()
        adjacent = self.adj[pos]

        if any(nb in self.pits for nb in adjacent):
            percepts.add("breeze")

        if self.is_wumpus_alive and self.wumpus in adjacent:
            percepts.add("stench")

        if not self.gold_taken and pos == self.gold:
            percepts.add("glitter")

        if self.last_action_screamed:
            percepts.add("scream")
            self.last_action_screamed = False  # Scream is heard once

        return percepts

    def shoot_arrow(self, from_pos, direction):
        """
        Shoots an arrow from `from_pos` in direction ('UP', 'DOWN', 'LEFT', 'RIGHT').
        The arrow flies straight until it hits the room wall or strikes the Wumpus.
        """
        dr, dc = DIRECTIONS[direction]
        room = self.room_of(from_pos)
        r, c = from_pos
        while True:
            r += dr
            c += dc
            if (r, c) not in self.cells or self.room_of((r, c)) != room:
                return False
            if self.is_wumpus_alive and (r, c) == self.wumpus:
                self.is_wumpus_alive = False
                self.last_action_screamed = True
                return True
