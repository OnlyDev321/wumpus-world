import pygame

from game.world import World
from game.agent import Agent
from ui.renderer import Renderer


pygame.init()

# ==============================
# Window settings
# ==============================

WIDTH = 600
HEIGHT = 600
CELL_SIZE = 150

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wumpus World")

# ==============================
# World and Agent
# ==============================

world = World()
agent = Agent()

# Synchronize the Agent's initial position with the World
world.agent_position = agent.position

# Create Renderer
renderer = Renderer(screen, CELL_SIZE)

# ==============================
# Main loop
# ==============================

running = True

while running:

    # ==============================
    # Handle events
    # ==============================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        # Handle keyboard events
        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_UP:
                agent.move_up()

            elif event.key == pygame.K_DOWN:
                agent.move_down()

            elif event.key == pygame.K_LEFT:
                agent.move_left()

            elif event.key == pygame.K_RIGHT:
                agent.move_right()

            # Update the Agent's position in the World
            world.agent_position = agent.position

    # ==============================
    # Render World
    # ==============================

    renderer.draw_world(world)

    # ==============================
    # Update screen
    # ==============================

    pygame.display.flip()

# ==============================
# Quit
# ==============================

pygame.quit()