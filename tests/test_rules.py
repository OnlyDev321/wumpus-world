import unittest

from game.rules import deduce_knowledge, calculate_cell_risk

SIZE = 4
CELLS = {(r, c) for r in range(SIZE) for c in range(SIZE)}


def neighbors(pos):
    r, c = pos
    return [(nr, nc) for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= nr < SIZE and 0 <= nc < SIZE]


class RulesTests(unittest.TestCase):
    def test_no_breeze_no_stench_makes_neighbours_safe(self):
        k = deduce_knowledge(CELLS, neighbors, {(3, 0)}, {(3, 0): set()})
        self.assertEqual(k["safe_cells"], {(3, 0), (2, 0), (3, 1)})

    def test_single_unknown_neighbour_of_breeze_is_a_pit(self):
        visited = {(3, 0), (3, 1)}
        percepts = {(3, 0): set(), (3, 1): {"breeze"}}
        # Both unknown neighbours of the breeze, (2, 1) and (3, 2), may hold the pit.
        k = deduce_knowledge(CELLS, neighbors, visited, percepts)
        self.assertEqual(k["possible_pits"], {(2, 1), (3, 2)})
        self.assertEqual(k["confirmed_pits"], set())
        # Visit (2, 0) and (2, 1) without a breeze: only (3, 2) is left.
        visited |= {(2, 0), (2, 1)}
        percepts.update({(2, 0): set(), (2, 1): set()})
        k = deduce_knowledge(CELLS, neighbors, visited, percepts)
        self.assertEqual(k["confirmed_pits"], {(3, 2)})
        self.assertEqual(calculate_cell_risk((3, 2), k), 10)

    def test_two_stenches_pin_the_wumpus(self):
        visited = {(3, 0), (2, 0), (3, 1)}
        percepts = {(3, 0): set(), (2, 0): {"stench"}, (3, 1): {"stench"}}
        k = deduce_knowledge(CELLS, neighbors, visited, percepts)
        self.assertEqual(k["confirmed_wumpus"], (2, 1))
        self.assertTrue(k["wumpus_localized"])
        self.assertNotIn((2, 1), k["wumpus_free"])

    def test_dead_wumpus_frees_every_cell(self):
        percepts = {(3, 0): set(), (2, 0): {"stench"}}
        k = deduce_knowledge(CELLS, neighbors, {(3, 0), (2, 0)}, percepts, is_wumpus_alive=False)
        self.assertEqual(k["wumpus_free"], CELLS)
        self.assertIsNone(k["confirmed_wumpus"])

    def test_remembered_pit_is_never_pit_free(self):
        memory = {"pits": {(2, 0)}, "wumpus": None}
        k = deduce_knowledge(CELLS, neighbors, {(3, 0)}, {(3, 0): set()}, death_memory=memory)
        self.assertNotIn((2, 0), k["pit_free"])
        self.assertNotIn((2, 0), k["safe_cells"])
        self.assertIn((2, 0), k["confirmed_pits"])

    def test_missed_shot_cells_are_wumpus_free(self):
        percepts = {(3, 0): {"stench"}}
        k = deduce_knowledge(CELLS, neighbors, {(3, 0)}, percepts, missed_shots={(2, 0), (1, 0), (0, 0)})
        self.assertEqual(k["confirmed_wumpus"], (3, 1))


if __name__ == "__main__":
    unittest.main()
