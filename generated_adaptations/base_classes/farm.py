import abc

from base_classes.adaptation import Adaptation
from farm.simulation import SmartFarmSimulation


class FarmAdaptation(Adaptation, abc.ABC):

    def __init__(self, adapt_every=1):
        super().__init__()
        self.adapt_every = adapt_every

    @abc.abstractmethod
    def assign_drones(self, components, environment, group_ids, step: int):
        pass

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        if (step - 1) % self.adapt_every != 0:
            return

        components = list(simulation.availableDrones())
        ensembles = ["idle"] + [f"protecting {field.id}" for field in simulation.fields]
        self.assign_drones(components, simulation, ensembles, step)

        if len(simulation.assignments) < len(components):
            missing_components = [component.id for component in components if component not in simulation.assignments]
            error = "The following components have not been assigned to a group: " + ", ".join(missing_components)
            simulation.append_assignment_error(error)
