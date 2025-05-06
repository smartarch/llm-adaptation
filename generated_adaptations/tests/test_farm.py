import random

import pytest

from farm.simulation import SmartFarmSimulation
from generated_adaptations.tests.test_generic import TestAdapt as Helpers


@pytest.fixture(autouse=True)
def skip_if_not_farm(example):
    if example != "farm":
        pytest.skip("Tests only for farm example")


@pytest.mark.dependency(depends=["generated_adaptations/tests/test_generic.py::TestConfiguration::test_adaptation_exists"], scope='session')
class TestFarm:

    @pytest.mark.parametrize("seed", [1, 2, 3])
    def test_all_assigned_when_all_protecting(self, adaptation_config, simulation_class, simulation_configs, seed):
        random.seed(seed)
        simulation: SmartFarmSimulation = Helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # assign drones to fields randomly
        for drone in simulation.drones:
            drone.assignTarget(random.choice(simulation.fields))

        # run a few steps of the simulation without adapting to let the drones arrive to their fields
        simulation.should_adapt = lambda: False
        simulation.run_simulation(20)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        # TODO: assert