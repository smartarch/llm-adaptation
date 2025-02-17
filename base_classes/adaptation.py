import abc
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from base_classes.simulation import Simulation


class Adaptation(abc.ABC):

    def __init__(self):
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
