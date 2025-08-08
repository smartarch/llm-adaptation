import abc
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from base_classes.simulation import Simulation


class Adaptation(abc.ABC):

    def __init__(self, **kwargs):
        self.simulation: Simulation = ...

    @abc.abstractmethod
    def adapt(self, simulation: "Simulation", step: int):
        """Called before every step of the simulation."""
        pass

    def init(self, simulation: "Simulation"):
        """Called before the simulation starts."""
        self.simulation = simulation

    def end(self, simulation: "Simulation"):
        """Called when the simulation ends."""
        pass


class DSLAdaptation(Adaptation):

    def adapt(self, simulation: "Simulation", step: int):
        for assignment_name, assignment_config in simulation.dsl_config.load_assignment_configs():
            simulation.current_assignment = assignment_name
            components = list(simulation.dsl_config.load_components_for_assignment(simulation, assignment_name).values())
            ensemble_instances = simulation.dsl_config.load_ensemble_instances_for_assignment(simulation, assignment_name)
            ensemble_names = [ensemble.name for ensemble in ensemble_instances]
            assignment_method = getattr(self, assignment_name)
            assignment_method(components, simulation, ensemble_names, step)
            simulation.check_missing_assignments(components)
        simulation.current_assignment = None


def import_adaptation(config: dict) -> Adaptation:
    adaptation_name = config["adaptation_name"]
    adaptation_params = config["adaptation_params"]
    # assert adaptation_name.startswith("adaptations.") or adaptation_name.startswith("generated_adaptations.")

    adaptation_module, adaptation_class = adaptation_name.rsplit(".", 1)
    print(f"Loading adaptation {adaptation_class} from module {adaptation_module}")
    module = importlib.import_module(adaptation_module)
    clazz = getattr(module, adaptation_class)
    if "config" in adaptation_params:
        adaptation_params["config"] = config

    return clazz(**adaptation_params)
