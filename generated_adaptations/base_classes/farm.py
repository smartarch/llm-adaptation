import abc

from base_classes.adaptation import Adaptation
from farm.simulation import SmartFarmSimulation


class FarmAdaptation(Adaptation, abc.ABC):

    def __init__(self, adapt_every=1, **kwargs):
        super().__init__(**kwargs)
        self.adapt_every = adapt_every

    @abc.abstractmethod
    def assign_drones(self, components, environment, group_ids, step: int):
        pass

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        # TODO: this could be possibly replaced by loading from the DSL
        components = list(simulation.availableDrones())
        ensembles = ["idle"] + [f"protecting {field.id}" for field in simulation.fields]

        self.assign_drones(components, simulation, ensembles, step)

        self.simulation.check_missing_assignments(components)
