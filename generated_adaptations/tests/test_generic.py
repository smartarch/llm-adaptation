from pathlib import Path

import pytest

from base_classes.adaptation import import_adaptation
from utils import read_configs, nested_update


class TestFixtures:
    """Checks that test parameters are set correctly."""

    @pytest.mark.dependency()
    def test_example_is_correct(self, example):
        assert example in ("farm", "dragon")

    @pytest.mark.dependency(depends=["TestFixtures::test_example_is_correct"])
    def test_adaptation_exists(self, example, adaptation_name):
        path = Path(f"generated_adaptations/{example}/{adaptation_name}.py")
        assert path.exists(), f"{path.resolve()} does not exist"


@pytest.mark.dependency(depends=["TestFixtures::test_adaptation_exists"])
class TestGeneric:

    def test_adapt(self, adaptation_name, adaptation_config, simulation_class, simulation_configs):
        config = read_configs(simulation_configs)
        config = nested_update(config, adaptation_config)
        adaptation = import_adaptation(config)

        simulation = simulation_class(adaptation.adapt, config)
        adaptation.init(simulation)

        # running one step
        simulation.adapt(simulation, 1)
