import unittest

from game.search import bfs_search, ucs_search


def grid_successors(size, blocked=(), step_cost=1):
    def successors(pos):
        r, c = pos
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < size and 0 <= nc < size and (nr, nc) not in blocked:
                yield (nr, nc), ("MOVE", (nr, nc)), step_cost
    return successors


class SearchTests(unittest.TestCase):
    def test_bfs_and_ucs_find_equally_short_paths_on_uniform_costs(self):
        successors = grid_successors(5, blocked={(1, 1), (2, 1), (3, 1)})
        goal = lambda pos: pos == (4, 4)
        bfs = bfs_search((0, 0), goal, successors)
        ucs = ucs_search((0, 0), goal, successors)
        self.assertEqual(len(bfs.actions), 8)
        self.assertEqual(len(ucs.actions), 8)
        self.assertEqual(bfs.cost, ucs.cost)

    def test_start_is_goal(self):
        result = bfs_search((2, 2), lambda pos: pos == (2, 2), grid_successors(3))
        self.assertEqual(result.actions, ())
        self.assertEqual(result.cost, 0)

    def test_unreachable_goal_returns_none(self):
        successors = grid_successors(3, blocked={(0, 1), (1, 0), (1, 1)})
        self.assertIsNone(bfs_search((0, 0), lambda pos: pos == (2, 2), successors))
        self.assertIsNone(ucs_search((0, 0), lambda pos: pos == (2, 2), successors))

    def test_bfs_reports_real_cost_not_step_count(self):
        # A single "shot" transition costs 10; BFS still takes it (fewest transitions)
        # but must report what the path really costs.
        def successors(state):
            if state == "start":
                yield "goal", "SHOOT", 10
                yield "a", "MOVE", 1
            elif state == "a":
                yield "b", "MOVE", 1
            elif state == "b":
                yield "goal", "MOVE", 1

        bfs = bfs_search("start", lambda s: s == "goal", successors)
        self.assertEqual(bfs.actions, ("SHOOT",))
        self.assertEqual(bfs.cost, 10)
        ucs = ucs_search("start", lambda s: s == "goal", successors)
        self.assertEqual(ucs.actions, ("MOVE", "MOVE", "MOVE"))
        self.assertEqual(ucs.cost, 3)


if __name__ == "__main__":
    unittest.main()
