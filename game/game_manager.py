import time

from game.world import World
from game.algorithms import algorithm_name
from game.i18n import T, Join, algorithm_label
from game.scoring import MOVE_COST, SHOT_COST, DEATH_COST, GOLD_REWARD, calculate_memory_penalty


class GameManager:
    """
    Coordinates the game flow:
    - Synchronizes state between World and Agent
    - Manages game modes (Auto, Step-by-step, Manual)
    - Tracks score, steps, and Victory / Game Over states
    """

    SPEEDS = {"slow": 700, "normal": 400, "fast": 150}

    def __init__(self, world, agent, sound_manager=None, recorder=None):
        self.world = world
        self.agent = agent
        self.sound_manager = sound_manager
        self.recorder = recorder  # game.replays.GameRecorder: saves finished games for replay_viewer.py
        self.map_kind = "random"  # "random" or "classic", kept for the replay list
        self.num_rooms = world.num_rooms
        penalty = calculate_memory_penalty(self.agent.death_memory, self.world) if self.agent.has_death_memory() else 0
        self.score = -penalty
        self.steps = 0
        self.game_over = False
        self.victory = False
        self.death_reason = None
        self.play_mode = "step"  # "auto", "step" (AI one move at a time) or "manual" (the player)
        self.speed = "normal"
        self.logs = []
        self.known_doors = set()  # both endpoints of doors traversed during this game
        self.agent_class = type(agent)
        self.history = []  # results of finished games in this session (for Analytics)
        self._reset_stats()
        self.last_shot = None  # latest arrow flight, read by the renderer to animate it
        self._shot_seq = 0

        self.initial_perceive()
        self._start_recording()

    # ------------------------------------------------------------------
    # Play mode
    # ------------------------------------------------------------------
    PLAY_MODES = ("auto", "step", "manual")

    def set_play_mode(self, mode):
        if mode in self.PLAY_MODES:
            self.play_mode = mode

    @property
    def auto_mode(self):
        return self.play_mode == "auto"

    @auto_mode.setter
    def auto_mode(self, value):
        """Turning auto on selects Auto; turning it off falls back to Step."""
        if value:
            self.play_mode = "auto"
        elif self.play_mode == "auto":
            self.play_mode = "step"

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    def _reset_stats(self):
        self.stats = {"think_ms": [], "risky": 0, "shots": 0, "kills": 0, "doors": 0, "manual": False}
        self.started_at = time.perf_counter()
        self.finished_at = None
        self._recorded = False

    @property
    def algorithm(self):
        return algorithm_name(type(self.agent))

    def set_algorithm(self, agent_class):
        """Switches the AI algorithm and replays the current map with a fresh agent."""
        if agent_class is not type(self.agent):
            self.agent_class = agent_class
            self.reset(mode="replay")

    def outcome(self):
        if not self.game_over:
            return None
        if self.victory:
            return "win"
        return {"FALL_IN_PIT": "pit", "EATEN_BY_WUMPUS": "wumpus", "TRAPPED": "trapped"}.get(self.death_reason, "escaped")

    def elapsed_s(self):
        end = self.finished_at or time.perf_counter()
        return end - self.started_at

    def result(self):
        think = self.stats["think_ms"]
        return {
            "algorithm": self.algorithm,
            "rooms": self.world.num_rooms,
            "outcome": self.outcome(),
            "score": self.score,
            "steps": self.steps,
            "explored": len(self.agent.visited) / len(self.world.cells),
            "think_ms_avg": sum(think) / len(think) if think else 0.0,
            "think_ms_max": max(think) if think else 0.0,
            "decisions": len(think),
            "risky": self.stats["risky"],
            "shots": self.stats["shots"],
            "kills": self.stats["kills"],
            "doors": self.stats["doors"],
            "manual": self.stats["manual"],
            "duration_s": self.elapsed_s(),
        }

    def _after_action(self):
        if self.game_over and not self._recorded:
            self._recorded = True
            self.finished_at = time.perf_counter()
            self.history.append(self.result())
            if self.recorder:
                self.add_log(T("log.saved" if self.recorder.finish(self) else "log.save_failed"))

    # ------------------------------------------------------------------
    # Replay recording
    # ------------------------------------------------------------------
    def _start_recording(self, retry=False):
        if self.recorder:
            self.recorder.start(self, retry)

    def _record(self, kind, **data):
        if self.recorder:
            self.recorder.add(kind, **data)

    @property
    def auto_delay_ms(self):
        return self.SPEEDS[self.speed]

    def add_log(self, message):
        self.logs.append(message)
        if len(self.logs) > 8:
            self.logs.pop(0)

    def name(self, pos):
        return self.world.label(pos)

    def initial_perceive(self):
        percepts = self.world.get_percepts(self.agent.position)
        self.agent.perceive(percepts)
        self.agent.reason(self.world.is_wumpus_alive)
        p_str = Join([T(f"percept.{p}") for p in sorted(percepts)]) if percepts else T("log.clear")
        self.add_log(T("log.entered", cell=self.name(self.agent.position), percepts=p_str))
        if self.sound_manager:
            self.sound_manager.play_percepts(percepts)

    def set_num_rooms(self, n):
        """Changes the room count and generates a new dungeon with it."""
        n = max(World.MIN_ROOMS, min(World.MAX_ROOMS, n))
        if n != self.num_rooms:
            self.num_rooms = n
            self.reset(mode="random")

    def reset(self, mode="replay"):
        """
        Modes:
        - "replay": same map, keeps episodic death memory
        - "random": new random dungeon with `num_rooms` rooms, memory wiped
        - "classic": the original hand-made 4x4 map, memory wiped
        """
        if mode in ("random", "classic"):
            self.map_kind = mode
        if mode == "random":
            self.world.generate_random_world(self.num_rooms)
            self.agent.clear_death_memory()
            self.agent.reset(keep_memory=False)
            rooms = self.world.num_rooms
            log_msg = T("log.new_dungeon", n=rooms)
        elif mode == "classic":
            self.world.generate_classic_world()
            self.agent.clear_death_memory()
            self.agent.reset(keep_memory=False)
            log_msg = T("log.classic")
        else:
            self.world.reset_world()
            had_memory = self.agent.has_death_memory()
            self.agent.reset(keep_memory=True)
            log_msg = T("log.replay_mem", summary=self.agent.get_memory_summary()) if had_memory else T("log.replay")

        if type(self.agent) is not self.agent_class:
            had_mem = self.agent.has_death_memory()
            mem = self.agent.death_memory if had_mem else None
            self.agent = self.agent_class(self.world, death_memory=mem)
            log_msg = Join([log_msg, T("log.algorithm", name=algorithm_label(self.algorithm))], " ")

        penalty = calculate_memory_penalty(self.agent.death_memory, self.world) if self.agent.has_death_memory() else 0
        self.score = -penalty
        self.steps = 0
        self.game_over = False
        self.victory = False
        self.death_reason = None
        self.auto_mode = False
        if self.sound_manager:
            self.sound_manager.stop_all()
        self.logs.clear()
        self.known_doors.clear()
        self.last_shot = None
        self._reset_stats()
        self.initial_perceive()
        self.add_log(log_msg)
        self._start_recording(retry=mode == "replay")

    # ------------------------------------------------------------------
    # Shared action handlers (used by both the AI and the player)
    # ------------------------------------------------------------------
    def _move_to(self, pos, who="", auto_door=True, auto_exit=True):
        prev_pos = self.agent.position
        prev_room = self.world.room_of(prev_pos)
        if self.world.room_of(pos) != prev_room:
            # Stepping straight across a door link (from a door cell to its partner).
            self.agent.learn_door(prev_pos, pos)
        self.agent.position = pos
        self.world.agent_position = pos
        self.steps += 1
        self.score -= MOVE_COST
        self.add_log(T("log.moved", who=who, cell=self.name(pos)))

        if pos in self.world.pits:
            self._die("FALL_IN_PIT", T("log.pit", cell=self.name(pos)), "pit")
            return
        if pos == self.world.wumpus and self.world.is_wumpus_alive:
            self._die("EATEN_BY_WUMPUS", T("log.wumpus", cell=self.name(pos)), "wumpus")
            return

        new_room = self.world.room_of(pos)
        if new_room != prev_room:
            self.add_log(T("log.room", n=new_room + 1))

        self._perceive_here()

        # The AI exits with gold; the player always confirms with C.
        if pos == self.world.exit_position:
            if auto_exit and self.agent.has_gold:
                self._climb(who)
            elif not auto_exit:
                self.add_log(T("log.at_exit"))
            return

        # Stepping onto a door from inside its room carries the AI through it.
        # Arriving on a door from the other side does not, so it is not bounced back.
        # The player stops on the door and chooses to enter it with C.
        if pos in self.world.door_cells and new_room == prev_room:
            if auto_door:
                self._go_through_door(pos)
            else:
                target = self.world.door_partner(pos)
                self.add_log(T("log.at_door", n=self.world.room_of(target) + 1))

    def _go_through_door(self, door):
        self.stats["doors"] += 1
        target = self.world.door_partner(door)
        self.known_doors.update((door, target))
        self.agent.learn_door(door, target)
        self.agent.position = target
        self.world.agent_position = target
        self.add_log(T("log.door", n=self.world.room_of(target) + 1))
        if self.sound_manager:
            self.sound_manager.play("door")
        self._perceive_here()

    def _perceive_here(self):
        percepts = self.world.get_percepts(self.agent.position)
        knew_exit = self.agent.exit_pos is not None
        self.agent.perceive(percepts)
        if not knew_exit and self.agent.exit_pos is not None:
            self.add_log(T("log.found_exit", cell=self.name(self.agent.exit_pos)))
        self.agent.reason(self.world.is_wumpus_alive)
        if self.sound_manager:
            self.sound_manager.play_percepts(percepts)

    def _die(self, reason, message, sound):
        self.game_over = True
        self.agent.is_alive = False
        self.death_reason = reason
        self.score -= DEATH_COST
        self.agent.record_death(reason, self.agent.position)
        self.add_log(message)
        if self.sound_manager:
            self.sound_manager.play(sound)

    def _grab(self, who=""):
        if self.agent.position == self.world.gold and not self.world.gold_taken:
            self.world.gold_taken = True
            self.agent.has_gold = True
            self.add_log(T("log.grab", who=who))
            if self.sound_manager:
                self.sound_manager.play("gold")
        else:
            self.add_log(T("log.no_gold"))

    def _shoot(self, direction, who=""):
        if not self.agent.has_arrow:
            self.add_log(T("log.no_arrows"))
            return
        self.agent.has_arrow = False
        self.stats["shots"] += 1
        self.score -= SHOT_COST
        start = self.agent.position
        hit = self.world.shoot_arrow(start, direction)
        self._shot_seq += 1
        self.last_shot = {"id": self._shot_seq, "start": start, "end": self.world.last_arrow_end,
                          "direction": direction, "hit": hit}
        if hit:
            self.stats["kills"] += 1
            self.add_log(T("log.hit", who=who, dir=T(f"dir.{direction}"), ))
            if self.sound_manager:
                self.sound_manager.play("scream")
        else:
            self.add_log(T("log.miss", who=who, dir=T(f"dir.{direction}")))
            # Deduce Wumpus-Free cells along the flight path of the missed shot
            dr, dc = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}[direction]
            # Walk from the shooter to where the arrow stopped. A shot straight into the
            # wall ends on the shooter's own cell, so it covers no cells at all.
            missed_cells = set()
            curr = start
            end = self.world.last_arrow_end
            while curr != end:
                curr = (curr[0] + dr, curr[1] + dc)
                missed_cells.add(curr)
            if hasattr(self.agent, "record_missed_shot"):
                self.agent.record_missed_shot(missed_cells)
        self.agent.reason(self.world.is_wumpus_alive)

    def _climb(self, who="", allow_without_gold=False):
        pos = self.agent.position
        if pos == self.world.exit_position:
            if not self.agent.has_gold and not allow_without_gold:
                return
            self.game_over = True
            self.agent.escaped = True
            if self.agent.has_gold:
                self.victory = True
                self.score += GOLD_REWARD
                self.add_log(T("log.win", who=who))
            else:
                self.add_log(T("log.escaped", who=who))
            if self.sound_manager:
                self.sound_manager.play("door")
        elif pos == self.world.start_position:
            self.add_log(T("log.sealed", cell=self.name(self.agent.exit_pos))
                         if self.agent.exit_pos is not None else T("log.sealed_unknown"))
        else:
            self.add_log(T("log.no_exit", cell=self.name(self.agent.exit_pos))
                         if self.agent.exit_pos is not None else T("log.no_exit_unknown"))

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------
    def step_ai(self, action=None):
        """One AI turn. A replay passes the recorded `action`; the agent still thinks, so its reasoning is shown."""
        if self.game_over:
            return

        started = time.perf_counter()
        current_percepts = self.world.get_percepts(self.agent.position)
        self.agent.perceive(current_percepts)
        self.agent.reason(self.world.is_wumpus_alive)
        decided = self.agent.decide_next_action(self.world.is_wumpus_alive) or {"type": "PASS"}
        action = action or decided
        self._record("ai", action=dict(action))
        self.stats["think_ms"].append((time.perf_counter() - started) * 1000)
        if str(getattr(self.agent, "last_action", "")).startswith("RISKY"):
            self.stats["risky"] += 1

        kind = action.get("type")
        if kind == "MOVE" and action.get("to") not in self.world.get_adjacent(self.agent.position):
            self.game_over = True
            self.death_reason = "TRAPPED"
            self.auto_mode = False
            self.add_log(T("log.illegal", cell=action.get("to")))
        elif kind == "MOVE":
            self._move_to(action["to"])
        elif kind == "GRAB":
            self._grab()
        elif kind == "SHOOT":
            self._shoot(action["direction"])
        elif kind == "CLIMB":
            # The agent only climbs without gold when it is deadlocked at the exit.
            self._climb(allow_without_gold=True)
        else:
            self.game_over = True
            self.death_reason = "TRAPPED"
            self.auto_mode = False
            self.add_log(T("log.trapped"))
        self._after_action()

    # ------------------------------------------------------------------
    # Player
    # ------------------------------------------------------------------
    def _take_control(self):
        """Any player action switches to Manual mode."""
        self.play_mode = "manual"
        self.stats["manual"] = True

    def manual_move(self, dr, dc):
        if self.game_over:
            return
        self._take_control()
        self._record("move", dr=dr, dc=dc)
        r, c = self.agent.position
        target = (r + dr, c + dc)
        if (target in self.world.get_adjacent(self.agent.position)
                and self.world.room_of(target) == self.world.room_of(self.agent.position)):
            self._move_to(target, who=T("log.you"), auto_door=False, auto_exit=False)
        else:
            self.add_log(T("log.wall"))
        self._after_action()

    def manual_grab(self):
        if not self.game_over:
            self._take_control()
            self._record("grab")
            self._grab(who=T("log.you"))
            self._after_action()

    def manual_shoot(self, direction):
        if not self.game_over:
            self._take_control()
            self._record("shoot", direction=direction)
            self._shoot(direction, who=T("log.you"))
            self._after_action()

    def manual_climb(self):
        if not self.game_over:
            self._take_control()
            self._record("climb")
            self._climb(who=T("log.you"), allow_without_gold=True)
            self._after_action()

    def manual_enter_door(self):
        if self.game_over:
            return
        self._take_control()
        self._record("door")
        if self.at_exit():
            self._climb(who=T("log.you"), allow_without_gold=True)
        elif self.agent.position in self.world.door_cells:
            self._go_through_door(self.agent.position)
        else:
            self.add_log(T("log.no_door"))
        self._after_action()

    def at_door(self):
        return self.agent.position in self.world.door_cells

    def at_exit(self):
        return self.agent.position == self.world.exit_position
