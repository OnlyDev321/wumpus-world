import os
import pygame


class Renderer:
    """
    High-End Pygame Graphical Renderer:
    - Renders 4x4 dungeon grid using all authentic visual assets:
      hero, door, floor, wumpus, pit, gold, glitter, breeze, stench, scream, arrow.
    - Immersive Fog of War simulating the AI Agent's real-time knowledge.
    - AI Mind View & HUD Panel displaying live deduction, percept icons, and statistics.
    """

    def __init__(self, screen, cell_size=145, board_offset=(20, 20)):
        self.screen = screen
        self.cell_size = cell_size
        self.board_x, self.board_y = board_offset
        self.reveal_all = False  # Press TAB to toggle full map inspection

        # Typography (High-performance built-in fonts)
        self.font_title = pygame.font.Font(None, 26)
        self.font_bold = pygame.font.Font(None, 21)
        self.font_normal = pygame.font.Font(None, 17)
        self.font_small = pygame.font.Font(None, 14)

        # Curated Dark Fantasy / Modern Slate Palette
        self.COLOR_BG = (11, 15, 25)            # Deep dark background
        self.COLOR_PANEL = (20, 27, 45)         # Card background
        self.COLOR_PANEL_ALT = (15, 21, 36)     # Darker card section
        self.COLOR_PANEL_BORDER = (45, 55, 78)  # Subtle border
        self.COLOR_TEXT_MAIN = (248, 250, 252)  # Bright slate white
        self.COLOR_TEXT_MUTED = (148, 163, 184) # Muted slate text
        self.COLOR_GOLD = (250, 204, 21)        # Vibrant gold
        self.COLOR_CYAN = (56, 189, 248)        # Vibrant cyan
        self.COLOR_GREEN = (74, 222, 128)       # Emerald green
        self.COLOR_RED = (248, 113, 113)        # Crimson danger red
        self.COLOR_PURPLE = (192, 132, 252)     # Mystical purple

        # Load and scale all sprites
        self.assets = {}
        self.mini_assets = {}
        self.load_all_sprites()

    def load_all_sprites(self):
        """Loads and pre-scales all sprite assets for maximum rendering performance."""
        file_map = {
            "floor": "floor.png",
            "door": "door.png",
            "hero": "hero.png",
            "wumpus": "wumpus.png",
            "pit": "pit.png",
            "gold": "gold.png",
            "glitter": "giltter.png",  # matches filename in assets
            "breeze": "breeze.png",
            "stench": "stench.png",
            "scream": "scream.png",
            "arrow": "arrow.png",
        }

        for key, filename in file_map.items():
            path = os.path.join("assets", filename)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    # Main scale for grid board
                    if key == "floor":
                        self.assets[key] = pygame.transform.smoothscale(img, (self.cell_size, self.cell_size))
                    elif key == "door":
                        # Wooden dungeon door scaled to fit cell bottom
                        dw = int(self.cell_size * 0.6)
                        dh = int(self.cell_size * 0.78)
                        self.assets[key] = pygame.transform.smoothscale(img, (dw, dh))
                    elif key in ["hero", "wumpus", "pit"]:
                        sz = int(self.cell_size * 0.8)
                        self.assets[key] = pygame.transform.smoothscale(img, (sz, sz))
                    elif key == "gold":
                        sz = int(self.cell_size * 0.68)
                        self.assets[key] = pygame.transform.smoothscale(img, (sz, sz))
                    elif key == "glitter":
                        sz = int(self.cell_size * 0.75)
                        self.assets[key] = pygame.transform.smoothscale(img, (sz, sz))
                    elif key in ["breeze", "stench"]:
                        sz = int(self.cell_size * 0.48)
                        self.assets[key] = pygame.transform.smoothscale(img, (sz, sz))
                    elif key == "scream":
                        sz = int(self.cell_size * 0.5)
                        self.assets[key] = pygame.transform.smoothscale(img, (sz, sz))
                    elif key == "arrow":
                        sz = int(self.cell_size * 0.35)
                        self.assets[key] = pygame.transform.smoothscale(img, (sz, sz))

                    # Mini scale for HUD badges
                    self.mini_assets[key] = pygame.transform.smoothscale(img, (22, 22))

                except Exception as e:
                    print(f"Error loading {filename}: {e}")
                    self.assets[key] = None
                    self.mini_assets[key] = None
            else:
                self.assets[key] = None
                self.mini_assets[key] = None

    def draw(self, game_manager):
        """Draws the entire view: 4x4 Grid Board + HUD Side Panel."""
        self.screen.fill(self.COLOR_BG)

        # 1. World Grid
        self.draw_grid(game_manager)

        # 2. Side HUD & AI Mind
        self.draw_hud(game_manager)

    def draw_grid(self, game_manager):
        """Renders 4x4 dungeon grid with floor tiles, entities, and atmospheric Fog of War."""
        world = game_manager.world
        agent = game_manager.agent

        board_w = world.size * self.cell_size
        board_h = world.size * self.cell_size

        # Board outer framing
        pygame.draw.rect(
            self.screen,
            self.COLOR_PANEL_BORDER,
            (self.board_x - 4, self.board_y - 4, board_w + 8, board_h + 8),
            3,
            border_radius=10
        )

        for r in range(world.size):
            for c in range(world.size):
                cell_pos = (r, c)
                x = self.board_x + c * self.cell_size
                y = self.board_y + r * self.cell_size
                rect = pygame.Rect(x, y, self.cell_size, self.cell_size)

                # Floor background texture
                if self.assets.get("floor"):
                    self.screen.blit(self.assets["floor"], (x, y))
                else:
                    pygame.draw.rect(self.screen, (30, 41, 59), rect)

                # Dungeon entrance door at (3, 0)
                if cell_pos == world.start_pos and self.assets.get("door"):
                    d_img = self.assets["door"]
                    d_rect = d_img.get_rect(midbottom=(rect.centerx, rect.bottom - 4))
                    self.screen.blit(d_img, d_rect)
                    # Label entrance
                    ent_lbl = self.font_small.render("EXIT", True, self.COLOR_CYAN)
                    self.screen.blit(ent_lbl, (x + 8, y + 6))

                # Grid cell borders
                pygame.draw.rect(self.screen, self.COLOR_PANEL_BORDER, rect, 1)

                is_visited = cell_pos in agent.visited
                is_safe = cell_pos in agent.knowledge["safe_cells"]
                is_current = cell_pos == agent.position

                # ==============================================================
                # Fog of War Overlay for unvisited cells
                # ==============================================================
                if not is_visited and not self.reveal_all:
                    fog_surf = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                    if is_safe:
                        # Inferred 100% SAFE cell: Subtle emerald illumination
                        fog_surf.fill((16, 185, 129, 75))
                        self.screen.blit(fog_surf, (x, y))
                        pygame.draw.rect(self.screen, (16, 185, 129), rect, 2)
                        safe_badge = self.font_small.render("SAFE", True, self.COLOR_GREEN)
                        self.screen.blit(safe_badge, (x + 8, y + 8))
                    else:
                        # Unknown cell: Deep cavern fog
                        fog_surf.fill((9, 13, 22, 235))
                        self.screen.blit(fog_surf, (x, y))
                        q_mark = self.font_bold.render("?", True, self.COLOR_TEXT_MUTED)
                        self.screen.blit(q_mark, (x + self.cell_size // 2 - 5, y + self.cell_size // 2 - 10))

                        # Inferred danger markers
                        if cell_pos in agent.knowledge["confirmed_pits"]:
                            warn_bg = pygame.Rect(x + 6, y + self.cell_size - 24, 48, 18)
                            pygame.draw.rect(self.screen, (127, 29, 29), warn_bg, border_radius=4)
                            warn = self.font_small.render("PIT!", True, self.COLOR_RED)
                            self.screen.blit(warn, (x + 12, y + self.cell_size - 23))

                        elif cell_pos == agent.knowledge["confirmed_wumpus"]:
                            warn_bg = pygame.Rect(x + 6, y + self.cell_size - 24, 72, 18)
                            pygame.draw.rect(self.screen, (127, 29, 29), warn_bg, border_radius=4)
                            warn = self.font_small.render("WUMPUS!", True, self.COLOR_RED)
                            self.screen.blit(warn, (x + 10, y + self.cell_size - 23))
                    continue

                # ==============================================================
                # Render Real World Entities (Visited or Full Reveal)
                # ==============================================================

                # 1. Bottomless Pit
                if cell_pos in world.pits:
                    if self.assets.get("pit"):
                        p_rect = self.assets["pit"].get_rect(center=rect.center)
                        self.screen.blit(self.assets["pit"], p_rect)

                # 2. Wumpus Monster
                elif cell_pos == world.wumpus:
                    if self.assets.get("wumpus"):
                        w_rect = self.assets["wumpus"].get_rect(center=rect.center)
                        if not world.is_wumpus_alive:
                            dead_surf = self.assets["wumpus"].copy()
                            dead_surf.set_alpha(110)
                            self.screen.blit(dead_surf, w_rect)
                            # Render scream or dead marker
                            if self.assets.get("scream"):
                                s_rect = self.assets["scream"].get_rect(center=rect.center)
                                self.screen.blit(self.assets["scream"], s_rect)
                            d_lbl = self.font_small.render("SLAIN", True, self.COLOR_RED)
                            self.screen.blit(d_lbl, (rect.centerx - 18, rect.bottom - 20))
                        else:
                            self.screen.blit(self.assets["wumpus"], w_rect)

                # 3. Gold Treasure & Glitter Aura
                if cell_pos == world.gold and not world.gold_taken:
                    if self.assets.get("glitter"):
                        g_rect = self.assets["glitter"].get_rect(center=rect.center)
                        self.screen.blit(self.assets["glitter"], g_rect)
                    if self.assets.get("gold"):
                        gold_rect = self.assets["gold"].get_rect(center=rect.center)
                        self.screen.blit(self.assets["gold"], gold_rect)

                # 4. Breeze (Wind) Sprite overlay
                percepts_at_cell = agent.percepts_history.get(cell_pos, set())
                if "breeze" in percepts_at_cell and self.assets.get("breeze"):
                    b_rect = self.assets["breeze"].get_rect(topleft=(x + 2, y + 2))
                    self.screen.blit(self.assets["breeze"], b_rect)

                # 5. Stench (Green odor mist) Sprite overlay
                if "stench" in percepts_at_cell and self.assets.get("stench"):
                    s_rect = self.assets["stench"].get_rect(topright=(x + self.cell_size - 2, y + 2))
                    self.screen.blit(self.assets["stench"], s_rect)

                # 6. Hero Agent with glowing aura
                if is_current:
                    # Glowing pedestal effect under hero
                    aura_surf = pygame.Surface((70, 24), pygame.SRCALPHA)
                    pygame.draw.ellipse(aura_surf, (56, 189, 248, 120), (0, 0, 70, 24))
                    self.screen.blit(aura_surf, (rect.centerx - 35, rect.centery + 24))

                    if self.assets.get("hero"):
                        h_rect = self.assets["hero"].get_rect(center=rect.center)
                        self.screen.blit(self.assets["hero"], h_rect)
                    else:
                        pygame.draw.circle(self.screen, self.COLOR_CYAN, rect.center, 28)

                # Coordinate watermark
                coord_text = self.font_small.render(f"({r},{c})", True, (90, 105, 130))
                self.screen.blit(coord_text, (x + self.cell_size - 30, y + 4))

    def draw_hud(self, game_manager):
        """Renders the comprehensive HUD dashboard and AI Mind view on the right panel."""
        world = game_manager.world
        agent = game_manager.agent

        hud_x = self.board_x + world.size * self.cell_size + 20
        hud_y = self.board_y
        hud_w = 380
        hud_h = world.size * self.cell_size + 8

        # Main HUD container
        pygame.draw.rect(self.screen, self.COLOR_PANEL, (hud_x, hud_y, hud_w, hud_h), border_radius=12)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_BORDER, (hud_x, hud_y, hud_w, hud_h), 2, border_radius=12)

        curr_y = hud_y + 14

        # Title & Mode Header
        title = self.font_title.render("AGENTIC WUMPUS WORLD", True, self.COLOR_CYAN)
        self.screen.blit(title, (hud_x + 16, curr_y))
        curr_y += 30

        # Mode Badge Pill
        mode_str = "AUTO MODE" if game_manager.auto_mode else "STEP-BY-STEP"
        mode_col = self.COLOR_GREEN if game_manager.auto_mode else self.COLOR_GOLD
        pill_rect = pygame.Rect(hud_x + 16, curr_y, 130, 22)
        pygame.draw.rect(self.screen, (20, 35, 30) if game_manager.auto_mode else (35, 30, 15), pill_rect, border_radius=11)
        pygame.draw.rect(self.screen, mode_col, pill_rect, 1, border_radius=11)
        mode_txt = self.font_small.render(mode_str, True, mode_col)
        self.screen.blit(mode_txt, (hud_x + 26, curr_y + 4))

        fog_status = "FOG: REVEALED" if self.reveal_all else "FOG: ON"
        fog_pill = pygame.Rect(hud_x + 155, curr_y, 110, 22)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_ALT, fog_pill, border_radius=11)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_BORDER, fog_pill, 1, border_radius=11)
        fog_txt = self.font_small.render(fog_status, True, self.COLOR_TEXT_MUTED)
        self.screen.blit(fog_txt, (hud_x + 165, curr_y + 4))

        curr_y += 32

        # ==============================================================
        # Stats Card (Score, Steps, Gold, Arrow) with Mini Assets
        # ==============================================================
        stats_bg = pygame.Rect(hud_x + 14, curr_y, hud_w - 28, 70)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_ALT, stats_bg, border_radius=8)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_BORDER, stats_bg, 1, border_radius=8)

        # Score & Steps
        sc_txt = self.font_bold.render(f"Score: {game_manager.score}", True, self.COLOR_TEXT_MAIN)
        st_txt = self.font_normal.render(f"Steps: {game_manager.steps}", True, self.COLOR_TEXT_MUTED)
        self.screen.blit(sc_txt, (hud_x + 24, curr_y + 10))
        self.screen.blit(st_txt, (hud_x + 200, curr_y + 10))

        # Gold & Arrow with mini sprites
        if self.mini_assets.get("gold"):
            self.screen.blit(self.mini_assets["gold"], (hud_x + 24, curr_y + 38))
        gold_label = self.font_bold.render(
            "ACQUIRED" if agent.has_gold else "Not Found",
            True,
            self.COLOR_GOLD if agent.has_gold else self.COLOR_TEXT_MUTED
        )
        self.screen.blit(gold_label, (hud_x + 50, curr_y + 40))

        if self.mini_assets.get("arrow"):
            self.screen.blit(self.mini_assets["arrow"], (hud_x + 200, curr_y + 38))
        arrow_label = self.font_normal.render(
            "READY" if agent.has_arrow else "SPENT",
            True,
            self.COLOR_CYAN if agent.has_arrow else self.COLOR_RED
        )
        self.screen.blit(arrow_label, (hud_x + 226, curr_y + 40))

        curr_y += 82

        # ==============================================================
        # Real-time Percepts Panel with Sprite Badges
        # ==============================================================
        p_hdr = self.font_bold.render(f"Percepts at Cell {agent.position}:", True, self.COLOR_TEXT_MAIN)
        self.screen.blit(p_hdr, (hud_x + 16, curr_y))
        curr_y += 22

        percepts = world.get_percepts(agent.position)
        badge_x = hud_x + 16

        if not percepts:
            none_lbl = self.font_normal.render("None (Peaceful & Calm)", True, self.COLOR_TEXT_MUTED)
            self.screen.blit(none_lbl, (badge_x, curr_y + 4))
            curr_y += 32
        else:
            for p in ["breeze", "stench", "glitter", "scream"]:
                if p in percepts:
                    # Draw mini icon + label
                    badge_rect = pygame.Rect(badge_x, curr_y, 82, 26)
                    pygame.draw.rect(self.screen, self.COLOR_PANEL_ALT, badge_rect, border_radius=6)
                    pygame.draw.rect(self.screen, self.COLOR_PANEL_BORDER, badge_rect, 1, border_radius=6)

                    if self.mini_assets.get(p):
                        self.screen.blit(self.mini_assets[p], (badge_x + 3, curr_y + 2))
                    p_name = p.capitalize()
                    col = self.COLOR_CYAN if p == "breeze" else (self.COLOR_GREEN if p == "stench" else self.COLOR_GOLD)
                    lbl = self.font_small.render(p_name, True, col)
                    self.screen.blit(lbl, (badge_x + 28, curr_y + 6))
                    badge_x += 88
            curr_y += 34

        # ==============================================================
        # AI Mind & Thought Process Box
        # ==============================================================
        mind_box = pygame.Rect(hud_x + 14, curr_y, hud_w - 28, 90)
        pygame.draw.rect(self.screen, (16, 23, 40), mind_box, border_radius=8)
        pygame.draw.rect(self.screen, (40, 55, 80), mind_box, 1, border_radius=8)

        mind_hdr = self.font_bold.render("AI Agent Reasoning:", True, self.COLOR_GOLD)
        self.screen.blit(mind_hdr, (hud_x + 24, curr_y + 8))

        self.render_wrapped_text(
            agent.thought_process,
            self.font_normal,
            self.COLOR_TEXT_MAIN,
            hud_x + 24,
            curr_y + 32,
            hud_w - 48
        )
        curr_y += 102

        # ==============================================================
        # Knowledge Base Summary (Safe / Danger / Wumpus)
        # ==============================================================
        kb_box = pygame.Rect(hud_x + 14, curr_y, hud_w - 28, 50)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_ALT, kb_box, border_radius=8)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_BORDER, kb_box, 1, border_radius=8)

        safe_cnt = len(agent.knowledge["safe_cells"])
        w_state = "Slain" if not world.is_wumpus_alive else (
            f"At {agent.knowledge['confirmed_wumpus']}" if agent.knowledge["confirmed_wumpus"] else "Hunting"
        )
        pits_cnt = len(agent.knowledge["confirmed_pits"])

        kb_txt1 = self.font_small.render(f"Safe Cells: {safe_cnt}/16  |  Visited: {len(agent.visited)}/16", True, self.COLOR_GREEN)
        kb_txt2 = self.font_small.render(f"Pits Confirmed: {pits_cnt}  |  Wumpus: {w_state}", True, self.COLOR_CYAN)
        self.screen.blit(kb_txt1, (hud_x + 24, curr_y + 8))
        self.screen.blit(kb_txt2, (hud_x + 24, curr_y + 28))
        curr_y += 62

        # ==============================================================
        # Recent Event Logs
        # ==============================================================
        log_hdr = self.font_bold.render("Event Log:", True, self.COLOR_TEXT_MUTED)
        self.screen.blit(log_hdr, (hud_x + 16, curr_y))
        curr_y += 20

        for log in game_manager.logs[-3:]:
            log_lbl = self.font_small.render(f"> {log}", True, self.COLOR_TEXT_MUTED)
            self.screen.blit(log_lbl, (hud_x + 16, curr_y))
            curr_y += 18

        # ==============================================================
        # Footer Keyboard Hotkeys
        # ==============================================================
        footer_y = hud_y + hud_h - 52
        hotkey_box = pygame.Rect(hud_x + 14, footer_y, hud_w - 28, 42)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_ALT, hotkey_box, border_radius=6)
        pygame.draw.rect(self.screen, self.COLOR_PANEL_BORDER, hotkey_box, 1, border_radius=6)

        hk1 = self.font_small.render("[SPACE] Step  |  [A] Auto  |  [TAB] Fog", True, self.COLOR_CYAN)
        hk2 = self.font_small.render("[G] Grab  |  [C] Climb  |  [R] Reset  |  [M] Random", True, self.COLOR_TEXT_MUTED)
        self.screen.blit(hk1, (hud_x + 24, footer_y + 6))
        self.screen.blit(hk2, (hud_x + 24, footer_y + 22))

        # Victory or Game Over Overlay
        if game_manager.game_over:
            self.draw_game_over_banner(game_manager)

    def render_wrapped_text(self, text, font, color, x, y, max_width):
        """Renders multi-line wrapped text neatly within bounds."""
        words = text.split(" ")
        line = ""
        current_y = y
        for word in words:
            test_line = line + word + " "
            if font.size(test_line)[0] < max_width:
                line = test_line
            else:
                self.screen.blit(font.render(line, True, color), (x, current_y))
                line = word + " "
                current_y += font.get_linesize() + 1
        if line:
            self.screen.blit(font.render(line, True, color), (x, current_y))

    def draw_game_over_banner(self, game_manager):
        """Renders a centered victory or defeat modal dialog on the board."""
        banner_w = 420
        banner_h = 140
        bx = self.board_x + (self.cell_size * 4 - banner_w) // 2
        by = self.board_y + (self.cell_size * 4 - banner_h) // 2

        banner_surf = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        banner_surf.fill((11, 15, 25, 245))
        self.screen.blit(banner_surf, (bx, by))

        border_col = self.COLOR_GOLD if game_manager.victory else self.COLOR_RED
        pygame.draw.rect(self.screen, border_col, (bx, by, banner_w, banner_h), 3, border_radius=12)

        if game_manager.victory:
            t1 = self.font_title.render("VICTORY ACHIEVED!", True, self.COLOR_GOLD)
            t2 = self.font_normal.render(f"Gold retrieved safely! Final Score: {game_manager.score}", True, self.COLOR_TEXT_MAIN)
        else:
            t1 = self.font_title.render("EXPEDITION FAILED", True, self.COLOR_RED)
            reason = "Fell into an abyss Pit!" if game_manager.death_reason == "FALL_IN_PIT" else "Devoured by the Wumpus!"
            t2 = self.font_normal.render(f"{reason} Final Score: {game_manager.score}", True, self.COLOR_TEXT_MAIN)

        t3 = self.font_small.render("Press [R] to Play Again  |  [M] for New Map", True, self.COLOR_CYAN)

        self.screen.blit(t1, (bx + (banner_w - t1.get_width()) // 2, by + 22))
        self.screen.blit(t2, (bx + (banner_w - t2.get_width()) // 2, by + 58))
        self.screen.blit(t3, (bx + (banner_w - t3.get_width()) // 2, by + 94))