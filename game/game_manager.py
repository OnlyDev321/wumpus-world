class GameManager:
    """
    Coordinates the game flow:
    - Synchronizes state between World and Agent
    - Manages game modes (Auto, Step-by-step, Manual)
    - Tracks score, steps, and Victory / Game Over states
    """

    def __init__(self, world, agent, sound_manager=None):
        self.world = world
        self.agent = agent
        self.sound_manager = sound_manager
        self.score = 0
        self.steps = 0
        self.game_over = False
        self.victory = False
        self.death_reason = None
        self.auto_mode = False
        self.auto_delay_ms = 400
        self.last_step_time = 0
        self.logs = []

        # Initial perception at spawn
        self.initial_perceive()

    def add_log(self, message):
        """Records an event log entry."""
        self.logs.append(message)
        if len(self.logs) > 6:
            self.logs.pop(0)

    def initial_perceive(self):
        """Agent perceives and reasons at starting position."""
        percepts = self.world.get_percepts(self.agent.position)
        self.agent.perceive(percepts)
        self.agent.reason(self.world.is_wumpus_alive)
        p_str = ", ".join(percepts) if percepts else "Clear"
        self.add_log(f"Spawned at {self.agent.position}: [{p_str}]")
        if self.sound_manager:
            self.sound_manager.play_percepts(percepts)

    def reset(self, mode="replay"):
        """
        Resets the game state.

        Modes:
        - "replay": restores current map to its initial layout (same pits, wumpus, gold)
        - "random": generates a new randomized map
        - "default": loads the standard default map
        """
        if mode == "random" or mode is True:
            self.world.generate_random_world()
            log_msg = "New random map generated."
        elif mode == "default":
            self.world.generate_default_world()
            log_msg = "Default map loaded."
        else:
            self.world.reset_world()
            log_msg = "Current map replayed."

        self.agent.reset(self.world.start_position)
        self.score = 0
        self.steps = 0
        self.game_over = False
        self.victory = False
        self.death_reason = None
        self.auto_mode = False
        if self.sound_manager:
            self.sound_manager.stop_all()
        self.logs.clear()
        self.initial_perceive()
        self.add_log(log_msg)

    def step_ai(self):
        """Executes a single decision step by the AI Agent."""
        if self.game_over:
            return

        # 1. Gather current percepts
        current_percepts = self.world.get_percepts(self.agent.position)
        self.agent.perceive(current_percepts)

        # 2. Logic reasoning
        self.agent.reason(self.world.is_wumpus_alive)

        # 3. Decide action
        action = self.agent.decide_next_action(self.world.is_wumpus_alive)

        # 4. Execute action in environment
        action_type = action.get("type")

        if action_type == "MOVE":
            self.agent.position = action["to"]
            self.world.agent_position = self.agent.position
            self.steps += 1
            self.score -= 1
            self.add_log(f"Step {self.steps}: Moved to {self.agent.position}")

            # Check fatal hazards
            if self.agent.position in self.world.pits:
                self.game_over = True
                self.agent.is_alive = False
                self.death_reason = "FALL_IN_PIT"
                self.score -= 1000
                self.add_log("💀 Agent fell into a Pit! GAME OVER.")
                return

            if self.agent.position == self.world.wumpus and self.world.is_wumpus_alive:
                self.game_over = True
                self.agent.is_alive = False
                self.death_reason = "EATEN_BY_WUMPUS"
                self.score -= 1000
                self.add_log("👹 Devoured by the Wumpus! GAME OVER.")
                return

            # Percepts at new cell
            new_percepts = self.world.get_percepts(self.agent.position)
            self.agent.perceive(new_percepts)
            self.agent.reason(self.world.is_wumpus_alive)
            if self.sound_manager:
                self.sound_manager.play_percepts(new_percepts)

        elif action_type == "GRAB":
            if self.agent.position == self.world.gold and not self.world.gold_taken:
                self.world.gold_taken = True
                self.agent.has_gold = True
                self.score += 1000
                self.add_log("✨ Grabbed Gold (+1000 pts)!")

        elif action_type == "SHOOT":
            direction = action["direction"]
            self.agent.has_arrow = False
            self.score -= 10
            hit = self.world.shoot_arrow(self.agent.position, direction)
            if hit:
                self.add_log(f"🏹 Shot {direction}: WUMPUS SLAIN! Horrific scream heard!")
                if self.sound_manager:
                    self.sound_manager.play("scream")
            else:
                self.add_log(f"🏹 Shot {direction}: Arrow missed.")
            self.agent.reason(self.world.is_wumpus_alive)

        elif action_type == "CLIMB":
            if self.agent.position == self.world.start_pos:
                self.game_over = True
                if self.agent.has_gold:
                    self.victory = True
                    self.add_log("🏆 VICTORY! Agent climbed out with Gold!")
                else:
                    self.add_log("Climbed out safely without gold.")

    def manual_move(self, dr, dc):
        """Allows manual player control."""
        if self.game_over:
            return

        r, c = self.agent.position
        nr, nc = r + dr, c + dc
        if 0 <= nr < self.world.size and 0 <= nc < self.world.size:
            self.agent.position = (nr, nc)
            self.world.agent_position = (nr, nc)
            self.steps += 1
            self.score -= 1
            self.add_log(f"Manual: Moved to {(nr, nc)}")

            if self.agent.position in self.world.pits:
                self.game_over = True
                self.agent.is_alive = False
                self.death_reason = "FALL_IN_PIT"
                self.score -= 1000
                self.add_log("💀 Fell into a Pit! Game Over.")
            elif self.agent.position == self.world.wumpus and self.world.is_wumpus_alive:
                self.game_over = True
                self.agent.is_alive = False
                self.death_reason = "EATEN_BY_WUMPUS"
                self.score -= 1000
                self.add_log("👹 Encountered Wumpus! Game Over.")

            percepts = self.world.get_percepts(self.agent.position)
            self.agent.perceive(percepts)
            self.agent.reason(self.world.is_wumpus_alive)
            if self.sound_manager:
                self.sound_manager.play_percepts(percepts)

    def manual_grab(self):
        """Player manual grab action."""
        if self.game_over:
            return
        if self.agent.position == self.world.gold and not self.world.gold_taken:
            self.world.gold_taken = True
            self.agent.has_gold = True
            self.score += 1000
            self.add_log("✨ Player grabbed Gold (+1000)!")

    def manual_shoot(self, direction):
        """Allows manual player shooting in a given direction ('UP', 'DOWN', 'LEFT', 'RIGHT')."""
        if self.game_over:
            return
        if not self.agent.has_arrow:
            self.add_log("🏹 No arrows left!")
            return

        self.agent.has_arrow = False
        self.score -= 10
        hit = self.world.shoot_arrow(self.agent.position, direction)
        if hit:
            self.add_log(f"🏹 Manual Shot {direction}: WUMPUS SLAIN! Horrific scream heard!")
            if self.sound_manager:
                self.sound_manager.play("scream")
        else:
            self.add_log(f"🏹 Manual Shot {direction}: Arrow missed.")
        self.agent.reason(self.world.is_wumpus_alive)

    def manual_climb(self):
        """Allows player manual climb out / exit at the cave entrance."""
        if self.game_over:
            return
        if self.agent.position == self.world.start_pos:
            self.game_over = True
            if self.agent.has_gold:
                self.victory = True
                self.add_log("🏆 VICTORY! Player climbed out with Gold!")
            else:
                self.add_log("Player climbed out safely without gold.")
        else:
            self.add_log("Cannot climb out! You must return to the entrance (3, 0).")


