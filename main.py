import pygame

from game.world import World
from game.agent import Agent
from game.game_manager import GameManager
from ui.renderer import Renderer


def main():
    pygame.init()

    # Standard window dimensions for 4x4 board and right-side HUD panel
    WINDOW_WIDTH = 1020
    WINDOW_HEIGHT = 630
    CELL_SIZE = 145

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Agentic AI - Wumpus World")
    clock = pygame.time.Clock()

    # Initialize core components
    world = World(size=4, randomize=False)
    agent = Agent(start_pos=world.start_position, size=world.size)
    game_manager = GameManager(world, agent)
    renderer = Renderer(screen, cell_size=CELL_SIZE, board_offset=(20, 20))

    last_auto_step_time = 0
    running = True

    while running:
        current_time = pygame.time.get_ticks()

        # ==============================================================
        # Handle keyboard & window events
        # ==============================================================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                # 1. AI Controls
                if event.key == pygame.K_SPACE:
                    game_manager.step_ai()

                elif event.key == pygame.K_a:
                    game_manager.auto_mode = not game_manager.auto_mode

                # 2. Session Management
                elif event.key == pygame.K_r:
                    game_manager.reset(randomize=False)

                elif event.key == pygame.K_m:
                    game_manager.reset(randomize=True)

                elif event.key == pygame.K_TAB:
                    renderer.reveal_all = not renderer.reveal_all

                # 3. Manual player controls (to compare with AI)
                elif event.key == pygame.K_UP:
                    game_manager.manual_move(-1, 0)
                elif event.key == pygame.K_DOWN:
                    game_manager.manual_move(1, 0)
                elif event.key == pygame.K_LEFT:
                    game_manager.manual_move(0, -1)
                elif event.key == pygame.K_RIGHT:
                    game_manager.manual_move(0, 1)
                elif event.key == pygame.K_g:
                    game_manager.manual_grab()

        # ==============================================================
        # Auto Mode step update
        # ==============================================================
        if game_manager.auto_mode and not game_manager.game_over:
            if current_time - last_auto_step_time >= game_manager.auto_delay_ms:
                game_manager.step_ai()
                last_auto_step_time = current_time

        # ==============================================================
        # Render frame
        # ==============================================================
        renderer.draw(game_manager)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()