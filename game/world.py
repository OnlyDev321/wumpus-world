class World:
    
    def __init__(self):
        
        self.size = 4
        
        self.agent_position = (3,0)
        
        self.pits = {
            (0,2),
        }
        
        self.wumpus = (1,1)
        
        self.gold = (2,2)