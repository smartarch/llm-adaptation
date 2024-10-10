import abc
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


class Adaptation(abc.ABC):

    @abc.abstractmethod
    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        pass


def import_adaptation(config: dict) -> Adaptation:
    adaptation_name = config["adaptation_name"]
    adaptation_params = config["adaptation_params"]
    assert adaptation_name.startswith("adaptations.")

    adaptation_module, adaptation_class = adaptation_name.rsplit(".", 1)
    print(f"Loading adaptation {adaptation_class} from module {adaptation_module}")
    module = importlib.import_module(adaptation_module)
    clazz = getattr(module, adaptation_class)
    if "config" in adaptation_params:
        adaptation_params["config"] = config

    return clazz(**adaptation_params)
