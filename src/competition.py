import random

from .competitor import Competitor


class Competition:
    def __init__(self, competitor_1: Competitor, competitor_2: Competitor):
        self.competitor_1 = competitor_1
        self.competitor_2 = competitor_2

    def run(self) -> Competitor:
        # TODO: here all the game magic will happend
        return random.choice([self.competitor_1, self.competitor_2])
