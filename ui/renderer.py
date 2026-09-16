import pygame

class Renderer:
    
    def __init__(self, screen, cell_size=150):
        
        self.screen = screen
        self.cell_size = cell_size
        
    def draw_world(self,world):
        
        self.screen.fill("white")
        
        for row in range(world.size):
            
            for col in range(world.size):
                
                x = col * self.cell_size
                y = row * self.cell_size
                
                pygame.draw.rect(
                    self.screen,
                    "white",
                    (x,y,self.cell_size, self.cell_size)
                )
                
                pygame.draw.rect(
                    self.screen,
                    "black",
                    (x,y,self.cell_size, self.cell_size),
                    2
                )
                
        self.draw_text(world)