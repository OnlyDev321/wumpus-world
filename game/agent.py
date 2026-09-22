class Agent:

    def __init__(self):

        self.position = (3, 0)

    def move_up(self):
        row, col = self.position

        if row > 0:
            self.position = (row - 1, col)

    def move_down(self):
        row, col = self.position

        if row < 3:
            self.position = (row + 1, col)

    def move_left(self):
        row, col = self.position

        if col > 0:
            self.position = (row, col - 1)

    def move_right(self):
        row, col = self.position

        if col < 3:
            self.position = (row, col + 1)