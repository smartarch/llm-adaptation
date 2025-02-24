import abc

from base_classes.adaptation import Adaptation
from farm.simulation import SmartFarmSimulation


class FarmAdaptation(Adaptation, abc.ABC):

    def __init__(self, adapt_every=1):
        super().__init__()
        self.adapt_every = adapt_every

    @abc.abstractmethod
    def assign_drones(self, components, environment, step: int):
        pass

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        components = list(simulation.availableDrones())
        self.assign_drones(components, simulation, step)
