import random

import pytest

from farm.components.drone import DroneState
from farm.simulation import SmartFarmSimulation
from generated_adaptations.tests.test_generic import TestAdapt as Helpers


@pytest.fixture(autouse=True)
def skip_if_not_farm(example):
    if example != "farm":
        pytest.skip("Tests only for farm example")


STEPS = 20  # this has to be a multiple of 10 for the `adapt` call to work
helpers = Helpers()


@pytest.mark.dependency(depends=["generated_adaptations/tests/test_generic.py::TestConfiguration::test_adaptation_exists"], scope='session')
class TestFarm:

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("protecting_count", [5, 8])
    @pytest.mark.parametrize("seed,protecting_count", [(1, 5), (2, 8)])
    def test_protecting_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, protecting_count):
        """Blablabla"""
        random.seed(seed)
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # assign drones to fields randomly
        protecting_drones = simulation.drones[:protecting_count]
        for drone in protecting_drones:
            drone.assignTarget(random.choice(simulation.fields))

        # run a few steps of the simulation without adapting to let the drones arrive to their fields
        simulation.should_adapt = lambda: False
        simulation.run_simulation(STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, STEPS + 1)

        # count protecting drones without assignment
        unassigned_count = 0
        for drone in protecting_drones:
            if drone not in simulation.assignments:
                unassigned_count += 1

        assert unassigned_count == 0, f'{unassigned_count} out of {len(protecting_drones)} drones with state=="{DroneState.PROTECTING.value}" were not assigned'

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("protecting_count", [5, 8])
    @pytest.mark.parametrize("seed,protecting_count", [(1, 5), (2, 8)])
    def test_idle_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, protecting_count):
        random.seed(seed)
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # assign drones to fields randomly
        protecting_drones = simulation.drones[:protecting_count]
        for drone in protecting_drones:
            drone.assignTarget(random.choice(simulation.fields))
        idle_drones = simulation.drones[protecting_count:]

        # run a few steps of the simulation without adapting to let the drones arrive to their fields
        simulation.should_adapt = lambda: False
        simulation.run_simulation(STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, STEPS + 1)

        # count idle drones without assignment
        unassigned_count = 0
        for drone in idle_drones:
            if drone not in simulation.assignments:
                unassigned_count += 1

        assert unassigned_count == 0, f'{unassigned_count} out of {len(idle_drones)} drones with state=="{DroneState.IDLE.value}" were not assigned'

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("protecting_count", [5, 8])
    @pytest.mark.parametrize("seed,protecting_count", [(1, 5), (2, 8)])
    def test_moving_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, protecting_count):
        random.seed(seed)
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # assign drones to fields randomly
        protecting_drones = simulation.drones[:protecting_count]
        for drone in protecting_drones:
            drone.assignTarget(random.choice(simulation.fields))

        # run one step of the simulation without adapting to let the drones change state (but not arrive to the fields)
        simulation.should_adapt = lambda: False
        simulation.run_simulation(1)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        # count moving drones without assignment
        moving_drones = [drone for drone in protecting_drones if drone.state == DroneState.MOVING_TO_FIELD]

        unassigned_count = 0
        for drone in moving_drones:
            if drone not in simulation.assignments:
                unassigned_count += 1

        assert unassigned_count == 0, f'{unassigned_count} out of {len(moving_drones)} drones with state=="{DroneState.MOVING_TO_FIELD.value}" were not assigned'
