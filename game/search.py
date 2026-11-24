"""Reusable graph-search algorithms used by the Wumpus agents.

Each successor is returned as ``(state, action, step_cost)``. The search
functions return a :class:`SearchResult`, so BFS and UCS can solve routes
without coupling the algorithms to the game rules.
"""

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from collections import deque


@dataclass(frozen=True)
class SearchResult:
    """A planned path and a few metrics useful for debugging/benchmarking."""

    actions: tuple
    cost: float
    state: object
    expanded: int


def _result(parent, action, state, cost, expanded):
    actions = []
    current = state
    while parent[current][0] is not None:
        previous, previous_action = parent[current]
        actions.append(previous_action)
        current = previous
    actions.reverse()
    return SearchResult(tuple(actions), cost, state, expanded)


def bfs_search(start, is_goal, successors):
    """Find a path with the fewest transitions using breadth-first search.

    Step costs do not affect the order; the reported cost is the real path cost.
    """

    frontier = deque([start])
    reached = {start}
    parent = {start: (None, None)}
    path_cost = {start: 0}
    expanded = 0

    while frontier:
        state = frontier.popleft()
        if is_goal(state):
            return _result(parent, None, state, path_cost[state], expanded)
        expanded += 1
        for next_state, action, step_cost in successors(state):
            if next_state in reached:
                continue
            reached.add(next_state)
            parent[next_state] = (state, action)
            path_cost[next_state] = path_cost[state] + step_cost
            frontier.append(next_state)
    return None


def ucs_search(start, is_goal, successors):
    """Find a least-cost path using uniform-cost search."""

    serial = count()
    frontier = [(0, next(serial), start)]
    best_cost = {start: 0}
    parent = {start: (None, None)}
    expanded = 0

    while frontier:
        cost, _order, state = heappop(frontier)
        if cost != best_cost.get(state):
            continue
        if is_goal(state):
            return _result(parent, None, state, cost, expanded)
        expanded += 1
        for next_state, action, step_cost in successors(state):
            next_cost = cost + step_cost
            if next_cost >= best_cost.get(next_state, float("inf")):
                continue
            best_cost[next_state] = next_cost
            parent[next_state] = (state, action)
            heappush(frontier, (next_cost, next(serial), next_state))
    return None


SEARCH_FUNCTIONS = {
    "bfs": bfs_search,
    "ucs": ucs_search,
}
