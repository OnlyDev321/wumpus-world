import random
import unittest

from game.agent import Agent
from game.benchmarking import MAX_STEPS
from game.game_manager import GameManager
from game.strategies import STRATEGIES
from game.world import World


def make_world(rooms, seed):
    state = random.getstate()
    random.seed(seed)
    try:
        return World(num_rooms=rooms)
    finally:
        random.setstate(state)


def play(agent_class, world):
    """Plays a game and returns every AI action and the final result."""
    gm = GameManager(world, agent_class(world))
    actions = []
    for _ in range(MAX_STEPS):
        if gm.game_over:
            break
        gm.step_ai()
        actions.append(gm.agent.last_action)
    return actions, gm


class UncachedAgent(Agent):
    """Recomputes neighbours and knowledge every time, as the code did before caching."""

    def neighbors(self, pos):
        self._neighbor_cache.clear()
        return super().neighbors(pos)

    def reason(self, is_wumpus_alive=True):
        self._reasoned_on = None
        super().reason(is_wumpus_alive)


class AgentScenarioTests(unittest.TestCase):
    def test_logic_agent_wins_classic_map_by_killing_the_wumpus(self):
        _, gm = play(STRATEGIES["Logic + risk"], World(classic=True))
        result = gm.history[-1]
        self.assertEqual(result["outcome"], "win")
        self.assertEqual(result["kills"], 1)

    def test_safe_only_never_dies(self):
        for seed in range(30):
            for rooms in (1, 3, 6):
                _, gm = play(STRATEGIES["Safe only"], make_world(rooms, seed))
                self.assertNotIn(gm.history[-1]["outcome"], ("pit", "wumpus"), (rooms, seed))

    def test_every_game_ends(self):
        for name, cls in STRATEGIES.items():
            for seed in range(20):
                actions, gm = play(cls, make_world(4, seed))
                self.assertTrue(gm.game_over, (name, seed))
                self.assertLess(len(actions), MAX_STEPS, (name, seed))


class AgentCachingTests(unittest.TestCase):
    def test_caches_do_not_change_any_decision(self):
        for rooms in range(World.MIN_ROOMS, World.MAX_ROOMS + 1):
            for seed in range(15):
                cached, gm_a = play(Agent, make_world(rooms, seed))
                plain, gm_b = play(UncachedAgent, make_world(rooms, seed))
                self.assertEqual(cached, plain, (rooms, seed))
                self.assertEqual(gm_a.score, gm_b.score, (rooms, seed))

    def test_learning_a_door_updates_cached_neighbours(self):
        world = make_world(2, 0)
        agent = Agent(world)
        door, landing = world.doors[0]
        before = agent.neighbors(door)
        self.assertNotIn(landing, before)
        agent.learn_door(door, landing)
        self.assertIn(landing, agent.neighbors(door))
        self.assertIn(door, agent.neighbors(landing))

    def test_reason_reruns_after_new_percepts(self):
        agent = Agent(World(classic=True))
        agent.perceive(set())
        agent.reason()
        first = agent.knowledge
        agent.reason()
        self.assertIs(agent.knowledge, first)  # nothing new -> skipped
        agent.position = (2, 0)
        agent.perceive({"stench"})
        agent.reason()
        self.assertIsNot(agent.knowledge, first)
        agent.reason(is_wumpus_alive=False)
        self.assertEqual(agent.knowledge["confirmed_wumpus"], None)

    def test_move_distances_match_planned_paths(self):
        for seed in range(10):
            world = make_world(3, seed)
            gm = GameManager(world, Agent(world))
            for _ in range(40):
                if gm.game_over:
                    break
                gm.step_ai()
            agent = gm.agent
            safe = agent.knowledge["safe_cells"]
            distances = agent._move_distances(safe)
            for cell in agent.visited - {agent.position}:
                path = agent.find_shortest_path({cell}, safe)
                if path is None:
                    self.assertNotIn(cell, distances, (seed, cell))
                else:
                    self.assertEqual(distances[cell], len(path), (seed, cell))


if __name__ == "__main__":
    unittest.main()
