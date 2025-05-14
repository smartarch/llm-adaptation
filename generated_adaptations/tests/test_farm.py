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
    # @pytest.mark.parametrize("previously_protecting", [5, 8])
    @pytest.mark.parametrize("seed,previously_protecting", [(1, "5/8"), (2, "8/8")])
    def test_protecting_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        random.seed(seed)
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)
        protecting_count = int(previously_protecting.split("/")[0])

        # assign drones to fields randomly
        protecting = simulation.drones[:protecting_count]
        for drone in protecting:
            drone.assignTarget(random.choice(simulation.fields))

        # run a few steps of the simulation without adapting to let the drones arrive to their fields
        simulation.should_adapt = lambda: False
        simulation.run_simulation(STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, STEPS + 1)

        # count protecting drones without assignment
        unassigned_count = 0
        for drone in protecting:
            if drone not in simulation.assignments:
                unassigned_count += 1

        assert unassigned_count == 0, f'{unassigned_count} out of {len(protecting)} drones with state=="{DroneState.PROTECTING.value}" were not assigned'

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("previously_protecting", [5, 8])
    @pytest.mark.parametrize("seed,previously_protecting", [(1, "5/8"), (2, "8/8")])
    def test_idle_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        random.seed(seed)
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)
        protecting_count = int(previously_protecting.split("/")[0])

        # assign drones to fields randomly
        protecting = simulation.drones[:protecting_count]
        for drone in protecting:
            drone.assignTarget(random.choice(simulation.fields))
        idle = simulation.drones[protecting_count:]

        # run a few steps of the simulation without adapting to let the drones arrive to their fields
        simulation.should_adapt = lambda: False
        simulation.run_simulation(STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, STEPS + 1)

        # count idle drones without assignment
        unassigned_count = 0
        for drone in idle:
            if drone not in simulation.assignments:
                unassigned_count += 1

        assert unassigned_count == 0, f'{unassigned_count} out of {len(idle)} drones with state=="{DroneState.IDLE.value}" were not assigned'

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("previously_protecting", [5, 8])
    @pytest.mark.parametrize("seed,previously_protecting", [(1, "5/8"), (2, "8/8")])
    def test_moving_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        random.seed(seed)
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)
        protecting_count = int(previously_protecting.split("/")[0])

        # assign drones to fields randomly
        protecting = simulation.drones[:protecting_count]
        for drone in protecting:
            drone.assignTarget(random.choice(simulation.fields))

        # run one step of the simulation without adapting to let the drones change state (but not arrive to the fields)
        simulation.should_adapt = lambda: False
        simulation.run_simulation(1)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        # count moving drones without assignment
        moving = [drone for drone in protecting if drone.state == DroneState.MOVING_TO_FIELD]

        unassigned_count = 0
        for drone in moving:
            if drone not in simulation.assignments:
                unassigned_count += 1

        assert unassigned_count == 0, f'{unassigned_count} out of {len(moving)} drones with state=="{DroneState.MOVING_TO_FIELD.value}" were not assigned'

    @pytest.mark.dependency(depends=["generated_adaptations/tests/test_generic.py::TestAdapt::test_no_repeated_assignments"], scope='session')
    @pytest.mark.parametrize("seed,previously_protecting", [(0, "0/8"), (1, "5/8"), (2, "8/8")])
    def test_not_all_drones_are_idle(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        random.seed(seed)
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)
        protecting_count = int(previously_protecting.split("/")[0])

        # assign drones to fields randomly
        protecting = simulation.drones[:protecting_count]
        for drone in protecting:
            drone.assignTarget(random.choice(simulation.fields))

        # run one step of the simulation without adapting to let the drones change state (but not arrive to the fields)
        simulation.should_adapt = lambda: False
        simulation.run_simulation(STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, STEPS + 1)

        # count idle drones
        idle_drones = sum(1 for group_id in simulation.assignments.values() if group_id == "idle")

        assert idle_drones != len(simulation.drones), f'All {len(simulation.drones)} drones were assigned to the "idle" group, no drones were assigned to protect fields.'
