import abc

from base_classes.adaptation import Adaptation
from dragon.simulation import DragonHuntSimulation, Map, VALID_IN_VILLAGE, VALID_IN_CAVE


class DragonHuntAdaptation(Adaptation, abc.ABC):

    def __init__(self, adapt_every=1):
        super().__init__()
        self.adapt_every = adapt_every

    @abc.abstractmethod
    def assign_in_village(self, components, environment, group_ids, step: int):
        pass

    @abc.abstractmethod
    def assign_in_cave(self, components, environment, group_ids, step: int):
        pass

    def adapt(self, simulation: "DragonHuntSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        self.assign_in_village(simulation.get_villagers_in(Map.VILLAGE), simulation, VALID_IN_VILLAGE, step)
        self.assign_in_cave(simulation.get_villagers_in(Map.CAVE), simulation, VALID_IN_CAVE, step)
