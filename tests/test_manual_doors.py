import random
import unittest

from game.agent import Agent
from game.game_manager import GameManager
from game.world import World


class ManualDoorTests(unittest.TestCase):
    def setUp(self):
        random_state = random.getstate()
        try:
            random.seed(42)
            self.world = World(num_rooms=6)
        finally:
            random.setstate(random_state)
        self.gm = GameManager(self.world, Agent(self.world))

    def place(self, cell):
        self.gm.agent.position = cell
        self.world.agent_position = cell

    def test_direction_keys_cannot_cross_any_door_in_either_direction(self):
        for a, b in self.world.doors:
            for here, there in ((a, b), (b, a)):
                with self.subTest(here=here, there=there):
                    self.place(here)
                    self.gm.manual_move(there[0] - here[0], there[1] - here[1])
                    self.assertEqual(self.gm.agent.position, here)
                    self.assertEqual(self.world.agent_position, here)
                    self.assertEqual(self.gm.steps, 0)
                    self.assertFalse(self.gm.known_doors)

    def test_enter_door_remembers_both_sides_and_allows_return(self):
        a, b = self.world.doors[0]
        self.place(a)
        self.gm.manual_enter_door()
        self.assertEqual(self.gm.agent.position, b)
        self.assertEqual(self.gm.known_doors, {a, b})
        self.gm.manual_enter_door()
        self.assertEqual(self.gm.agent.position, a)
        self.assertEqual(self.gm.stats["doors"], 2)

    def test_player_can_step_onto_door_without_automatically_crossing(self):
        a, _ = self.world.doors[0]
        inside = next(cell for cell in self.world.get_adjacent(a)
                      if self.world.room_of(cell) == self.world.room_of(a))
        self.place(inside)
        self.gm.manual_move(a[0] - inside[0], a[1] - inside[1])
        self.assertEqual(self.gm.agent.position, a)
        self.assertEqual(self.gm.steps, 1)
        self.assertFalse(self.gm.known_doors)

    def test_ai_still_crosses_automatically_and_remembers_door(self):
        a, b = self.world.doors[0]
        inside = next(cell for cell in self.world.get_adjacent(a)
                      if self.world.room_of(cell) == self.world.room_of(a))
        self.place(inside)
        self.gm._move_to(a)
        self.assertEqual(self.gm.agent.position, b)
        self.assertEqual(self.gm.known_doors, {a, b})

    def test_reset_clears_door_discoveries_for_each_new_game(self):
        for mode in ("replay", "random", "classic"):
            with self.subTest(mode=mode):
                self.gm.known_doors.update(self.world.door_cells)
                self.gm.reset(mode)
                self.assertFalse(self.gm.known_doors)

    def step_onto_exit(self):
        exit_cell = self.world.exit_position
        inside = next(cell for cell in self.world.get_adjacent(exit_cell)
                      if self.world.room_of(cell) == self.world.room_of(exit_cell))
        self.place(inside)
        self.gm.manual_move(exit_cell[0] - inside[0], exit_cell[1] - inside[1])

    def test_manual_exit_requires_confirmation_with_or_without_gold(self):
        for has_gold in (False, True):
            with self.subTest(has_gold=has_gold):
                self.gm.reset()
                self.gm.agent.has_gold = has_gold
                self.step_onto_exit()
                self.assertTrue(self.gm.at_exit())
                self.assertFalse(self.gm.game_over)
                self.assertFalse(self.gm.agent.escaped)
                self.gm.manual_enter_door()
                self.assertTrue(self.gm.game_over)
                self.assertTrue(self.gm.agent.escaped)
                self.assertEqual(self.gm.victory, has_gold)

    def test_player_can_walk_away_from_exit_without_leaving(self):
        self.step_onto_exit()
        exit_cell = self.world.exit_position
        inside = next(cell for cell in self.world.get_adjacent(exit_cell)
                      if self.world.room_of(cell) == self.world.room_of(exit_cell))
        self.gm.manual_move(inside[0] - exit_cell[0], inside[1] - exit_cell[1])
        self.assertEqual(self.gm.agent.position, inside)
        self.assertFalse(self.gm.game_over)
        self.assertFalse(self.gm.agent.escaped)

    def test_ai_still_exits_automatically(self):
        exit_cell = self.world.exit_position
        self.place(next(cell for cell in self.world.get_adjacent(exit_cell)
                        if self.world.room_of(cell) == self.world.room_of(exit_cell)))
        self.gm.agent.has_gold = True
        self.gm._move_to(exit_cell)
        self.assertTrue(self.gm.game_over)
        self.assertTrue(self.gm.agent.escaped)
        self.assertTrue(self.gm.victory)


if __name__ == "__main__":
    unittest.main()
