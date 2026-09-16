import pygame
from game.world import World


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
# World
# ==============================

world = World()

font = pygame.font.Font(None, 80)


# ==============================
# Main loop
# ==============================

running = True

while running:

    # Handle events
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False


    # Background
    screen.fill("white")


    # ==============================
    # Draw grid
    # ==============================

    for row in range(world.size):

        for col in range(world.size):

            x = col * CELL_SIZE
            y = row * CELL_SIZE

            position = (row, col)


            # Draw cell
            pygame.draw.rect(
                screen,
                "white",
                (
                    x,
                    y,
                    CELL_SIZE,
                    CELL_SIZE
                )
            )


            # Draw border
            pygame.draw.rect(
                screen,
                "black",
                (
                    x,
                    y,
                    CELL_SIZE,
                    CELL_SIZE
                ),
                2
            )


            # ==============================
            # Check object
            # ==============================

            symbol = None

            if position in world.pits:

                symbol = "P"

            elif position == world.wumpus:

                symbol = "W"

            elif position == world.gold:

                symbol = "G"

            elif position == world.agent_position:

                symbol = "A"


            # ==============================
            # Draw object
            # ==============================

            if symbol is not None:

                text = font.render(
                    symbol,
                    True,
                    "black"
                )

                text_rect = text.get_rect(
                    center=(
                        x + CELL_SIZE // 2,
                        y + CELL_SIZE // 2
                    )
                )

                screen.blit(
                    text,
                    text_rect
                )


    # Update screen
    pygame.display.flip()


# ==============================
# Quit
# ==============================

pygame.quit()