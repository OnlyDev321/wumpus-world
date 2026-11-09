"""
Agent algorithms available in the game and in the Analytics benchmark.

To compare your own algorithm, subclass `Agent` (or write a class with the same
interface), override `decide_next_action`, and add it to ALGORITHMS below. It then
appears in the Analytics window (Dev mode) and in `python -m game.benchmark`.

`decide_next_action` returns one of:
    {"type": "MOVE", "to": cell}      cell must be in self.neighbors(self.position)
    {"type": "GRAB"}
    {"type": "SHOOT", "direction": "UP" | "DOWN" | "LEFT" | "RIGHT"}
    {"type": "PASS"}                  gives up (counted as "trapped")
Stepping onto the exit cell with gold ends the game in victory.
"""
from game.agent import Agent
from game.i18n import T


class SafeOnlyAgent(Agent):
    """Baseline: never steps into an unproven cell. Gives up when nothing safe is left."""

    def decide_next_action(self, is_wumpus_alive=True):
        action = super().decide_next_action(is_wumpus_alive)
        if self.last_action.startswith(("RISKY_MOVE", "NAVIGATE_TO_FRONTIER")):
            if self.has_gold:
                leave = self._go_to_exit(T("th.leave_gold"))
                if leave:
                    return leave
            self.last_action = "TRAPPED"
            self.thought_process = T("th.safe_giveup")
            return {"type": "PASS"}
        return action


ALGORITHMS = {
    "Logic + risk": Agent,
    "Safe only": SafeOnlyAgent,
}


def algorithm_name(agent_class):
    for name, cls in ALGORITHMS.items():
        if cls is agent_class:
            return name
    return agent_class.__name__
