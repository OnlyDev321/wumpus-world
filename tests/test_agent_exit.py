import unittest

from game.agent import Agent
from game.algorithms import SafeOnlyAgent
from game.game_manager import GameManager
from game.world import World


class AgentExitTests(unittest.TestCase):
    def setUp(self):
        self.world = World(classic=True)
        self.world.pits = set()
        self.world.is_wumpus_alive = False
        self.world.gold = (0, 2)
        self.agent = Agent(self.world)
        self.gm = GameManager(self.world, self.agent)

    def place(self, cell):
        self.agent.position = self.world.agent_position = cell

    def test_ai_reaches_exit_without_gold_and_keeps_searching(self):
        self.place((1, 3))
        self.agent.visited = self.world.cells - {(0, 3), (0, 2)}
        self.agent.knowledge["safe_cells"] = {(1, 3), (0, 3), (0, 2)}
        action = self.agent.decide_next_action(False)
        self.assertEqual(action, {"type": "MOVE", "to": self.world.exit_position})
        self.gm._move_to(action["to"])
        self.assertFalse(self.gm.game_over)
        self.assertFalse(self.agent.escaped)
        action = self.agent.decide_next_action(False)
        self.assertEqual(action, {"type": "MOVE", "to": self.world.gold})
        self.gm._move_to(action["to"])
        self.gm.step_ai()  # Glitter -> grab gold
        self.assertTrue(self.agent.has_gold)
        self.gm.step_ai()  # Gold -> return to exit and win
        self.assertTrue(self.gm.victory)

    def test_ai_can_navigate_through_visited_exit_to_explore(self):
        self.place((1, 3))
        self.agent.visited = self.world.cells - {self.world.gold}
        self.agent.knowledge["safe_cells"] = {(1, 3), (0, 3), (0, 2)}
        action = self.agent.decide_next_action(False)
        self.assertEqual(action, {"type": "MOVE", "to": self.world.exit_position})
        self.assertTrue(self.agent.last_action.startswith("EXPLORE_SAFE"))

    def test_exhausted_search_reports_trapped_instead_of_escaping(self):
        for agent_class in (Agent, SafeOnlyAgent):
            for position in (self.world.start_position, self.world.exit_position):
                with self.subTest(agent=agent_class.__name__, position=position):
                    agent = agent_class(self.world)
                    gm = GameManager(self.world, agent)
                    agent.position = self.world.agent_position = position
                    agent.visited = set(self.world.cells)
                    agent.has_arrow = False
                    gm.step_ai()
                    self.assertTrue(gm.game_over)
                    self.assertEqual(gm.death_reason, "TRAPPED")
                    self.assertEqual(gm.outcome(), "trapped")
                    self.assertFalse(agent.escaped)
                    self.assertFalse(gm.victory)
                    self.assertEqual(agent.position, position)

    def test_safe_only_agent_does_not_retreat_without_gold(self):
        agent = SafeOnlyAgent(self.world)
        agent.visited = {agent.position}
        agent.knowledge["safe_cells"] = {agent.position}
        action = agent.decide_next_action(False)
        self.assertEqual(action, {"type": "PASS"})
        self.assertEqual(agent.last_action, "TRAPPED")

    def test_automatic_climb_cannot_escape_without_gold(self):
        self.place(self.world.exit_position)
        self.gm._climb()
        self.assertFalse(self.gm.game_over)
        self.assertFalse(self.agent.escaped)

    def test_ai_with_gold_on_exit_climbs_after_manual_handoff(self):
        self.place(self.world.exit_position)
        self.agent.has_gold = True
        self.gm.set_play_mode("auto")
        self.gm.step_ai()
        self.assertTrue(self.gm.game_over)
        self.assertTrue(self.gm.victory)


if __name__ == "__main__":
    unittest.main()
