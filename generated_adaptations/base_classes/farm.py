import abc

from base_classes.adaptation import Adaptation
from farm.simulation import SmartFarmSimulation


class FarmAdaptation(Adaptation, abc.ABC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def assign_drones(self, components, environment, group_ids, step: int):
        pass

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        # TODO: this could be possibly replaced by loading from the DSL
        components = list(simulation.availableDrones())
        ensembles = ["idle"] + [f"protecting {field.id}" for field in simulation.fields]

        self.assign_drones(components, simulation, ensembles, step)

        self.simulation.check_missing_assignments(components)
