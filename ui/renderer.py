import pygame


class Renderer:

    def __init__(self, screen, cell_size=150):

        self.screen = screen
        self.cell_size = cell_size

    def draw_world(self, world):

        self.screen.fill("white")

        for row in range(world.size):

            for col in range(world.size):

                x = col * self.cell_size
                y = row * self.cell_size

                position = (row, col)

                # ==============================
                # Draw cell
                # ==============================

                pygame.draw.rect(
                    self.screen,
                    "white",
                    (x, y, self.cell_size, self.cell_size)
                )

                # ==============================
                # Draw border
                # ==============================

                pygame.draw.rect(
                    self.screen,
                    "black",
                    (x, y, self.cell_size, self.cell_size),
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

                    font = pygame.font.Font(None, 80)

                    text = font.render(
                        symbol,
                        True,
                        "black"
                    )

                    text_rect = text.get_rect(
                        center=(
                            x + self.cell_size // 2,
                            y + self.cell_size // 2
                        )
                    )

                    self.screen.blit(
                        text,
                        text_rect
                    )