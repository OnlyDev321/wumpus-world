import random


class World:
    """
    Wumpus World 4x4 Environment.
    Manages positions of pits, wumpus, gold, and generates percepts.
    """

    def __init__(self, size=4, randomize=False):
        self.size = size
        self.start_position = (self.size - 1, 0)  # Typically bottom-left corner (3, 0)
        self.start_pos = self.start_position
        self.agent_position = self.start_position
        self.is_wumpus_alive = True
        self.gold_taken = False
        self.last_action_screamed = False

        self.initial_pits = set()
        self.initial_wumpus = None
        self.initial_gold = None

        if randomize:
            self.generate_random_world()
        else:
            self.generate_default_world()

    def reset_world(self):
        """Restores the current world map to its initial layout."""
        self.agent_position = self.start_position
        self.pits = set(self.initial_pits)
        self.wumpus = self.initial_wumpus
        self.gold = self.initial_gold
        self.is_wumpus_alive = True
        self.gold_taken = False
        self.last_action_screamed = False

    def generate_default_world(self):
        """Standard default map for logic inference verification."""
        self.agent_position = self.start_position
        self.pits = {(0, 2), (2, 2), (3, 3)}  # Default pits
        self.wumpus = (1, 1)                  # Wumpus at (1, 1)
        self.gold = (1, 2)                    # Gold at (1, 2)
        self.initial_pits = set(self.pits)
        self.initial_wumpus = self.wumpus
        self.initial_gold = self.gold
        self.is_wumpus_alive = True
        self.gold_taken = False
        self.last_action_screamed = False

    def generate_random_world(self, pit_prob=0.15):
        """Generates a random world ensuring start cell (3,0) and its neighbors are clear."""
        self.agent_position = self.start_position
        all_cells = [(r, c) for r in range(self.size) for c in range(self.size)]
        all_cells.remove(self.start_position)

        # Start neighbors kept safe initially for survival
        safe_start_neighbors = [(self.size - 2, 0), (self.size - 1, 1)]
        candidates = [c for c in all_cells if c not in safe_start_neighbors]

        # Place Wumpus
        self.wumpus = random.choice(candidates)
        candidates.remove(self.wumpus)

        # Place Gold
        self.gold = random.choice(candidates)

        # Place Pits with probability
        self.pits = set()
        for cell in all_cells:
            if cell != self.gold and cell != self.wumpus:
                if random.random() < pit_prob:
                    self.pits.add(cell)

        self.initial_pits = set(self.pits)
        self.initial_wumpus = self.wumpus
        self.initial_gold = self.gold
        self.is_wumpus_alive = True
        self.gold_taken = False
        self.last_action_screamed = False

    def get_adjacent(self, pos):
        """Returns valid adjacent cells (Up, Down, Left, Right) within the grid."""
        r, c = pos
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                neighbors.append((nr, nc))
        return neighbors

    def get_percepts(self, pos):
        """
        Returns the set of percepts at cell pos:
        - breeze: adjacent to a Pit
        - stench: adjacent to Wumpus (when alive)
        - glitter: current cell contains Gold
        - scream: Wumpus killed on the previous action
        """
        percepts = set()
        adjacent = self.get_adjacent(pos)

        # Check Breeze
        if any(neighbor in self.pits for neighbor in adjacent):
            percepts.add("breeze")

        # Check Stench
        if self.is_wumpus_alive and any(neighbor == self.wumpus for neighbor in adjacent):
            percepts.add("stench")

        # Check Glitter
        if not self.gold_taken and pos == self.gold:
            percepts.add("glitter")

        # Check Scream
        if self.last_action_screamed:
            percepts.add("scream")
            self.last_action_screamed = False  # Scream is heard once

        return percepts

    def shoot_arrow(self, from_pos, direction):
        """
        Shoots an arrow from `from_pos` in direction ('UP', 'DOWN', 'LEFT', 'RIGHT').
        Arrow flies straight until it hits a wall or strikes the Wumpus.
        """
        dr, dc = 0, 0
        if direction == "UP":
            dr = -1
        elif direction == "DOWN":
            dr = 1
        elif direction == "LEFT":
            dc = -1
        elif direction == "RIGHT":
            dc = 1

        r, c = from_pos
        while True:
            r += dr
            c += dc
            if not (0 <= r < self.size and 0 <= c < self.size):
                break  # Hit wall
            if self.is_wumpus_alive and (r, c) == self.wumpus:
                self.is_wumpus_alive = False
                self.last_action_screamed = True
                return True  # Struck Wumpus
        return False