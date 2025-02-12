import abc

from base_classes.adaptation import Adaptation
from dragon.simulation import DragonHuntSimulation, Map


class DragonHuntAdaptation(Adaptation, abc.ABC):

    def __init__(self, adapt_every=1):
        super().__init__()
        self.adapt_every = adapt_every

    @abc.abstractmethod
    def assign_in_village(self, components, environment, step: int):
        pass

    @abc.abstractmethod
    def assign_in_cave(self, components, environment, step: int):
        pass

    def adapt(self, simulation: "DragonHuntSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        self.assign_in_village(simulation.get_villagers_in(Map.VILLAGE), simulation, step)
        self.assign_in_cave(simulation.get_villagers_in(Map.CAVE), simulation, step)
