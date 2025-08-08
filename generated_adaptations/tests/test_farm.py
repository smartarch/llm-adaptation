import random

import pytest

from farm.components.drone import DroneState
from farm.simulation import SmartFarmSimulation
from generated_adaptations.tests.test_generic import TestAdapt as Helpers, assert_no_user_constraints_violated, fail


@pytest.fixture(autouse=True)
def skip_if_not_farm(example):
    if example != "farm":
        pytest.skip("Tests only for farm example")


STEPS = 20  # this has to be a multiple of 10 for the `adapt` call to work
TEST_STEP = STEPS + 1
assert TEST_STEP % 10 == 1, "TEST_STEP must be a multiple of 10 + 1 for the adapt call to work (since adapt is called every 10 steps)"
helpers = Helpers()


@pytest.mark.skip  # TODO: temporarily skipped until a better approach is implemented
@pytest.mark.dependency(depends=["generated_adaptations/tests/test_generic.py::TestConfiguration::test_adaptation_class_is_correct"], scope='session')
class TestFarm:

    @staticmethod
    def initialize(adaptation_config, previously_protecting, seed, simulation_class, simulation_configs):
        random.seed(seed)
        # noinspection PyTypeChecker
        simulation: SmartFarmSimulation = helpers.init_simulation(adaptation_config, simulation_class, simulation_configs)[0]
        protecting_count = int(previously_protecting.split("/")[0])
        return protecting_count, simulation

    @staticmethod
    def assert_no_drones_without_assignment(simulation, state=None):
        drones = [drone for drone in simulation.drones if state is None or drone.state == state]

        unassigned_count = 0
        for drone in drones:
            if drone not in simulation.assignments:
                unassigned_count += 1

        state_msg = f'with state=="{state.value}" ' if state is not None else ''
        if unassigned_count > 0:
            fail(f'{unassigned_count} out of {len(drones)} drones {state_msg}were not assigned')

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("previously_protecting", [5, 8])
    @pytest.mark.parametrize("seed,previously_protecting", [(1, "5/8"), (2, "8/8")])
    def test_protecting_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        protecting_count, simulation = self.initialize(adaptation_config, previously_protecting, seed, simulation_class, simulation_configs)
        # run a few steps of the simulation to move from the initial state
        simulation.random_assign_and_simulate(protecting_count, STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, TEST_STEP)

        self.assert_no_drones_without_assignment(simulation, DroneState.PROTECTING)

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("previously_protecting", [5, 8])
    @pytest.mark.parametrize("seed,previously_protecting", [(1, "5/8"), (2, "8/8")])
    def test_idle_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        protecting_count, simulation = self.initialize(adaptation_config, previously_protecting, seed, simulation_class, simulation_configs)
        # run a few steps of the simulation to move from the initial state
        simulation.random_assign_and_simulate(protecting_count, STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, TEST_STEP)

        self.assert_no_drones_without_assignment(simulation, DroneState.IDLE)

    # @pytest.mark.parametrize("seed", [1, 2, 3])
    # @pytest.mark.parametrize("previously_protecting", [5, 8])
    @pytest.mark.parametrize("seed,previously_protecting", [(1, "5/8"), (2, "8/8")])
    def test_moving_drones_are_assigned(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        protecting_count, simulation = self.initialize(adaptation_config, previously_protecting, seed, simulation_class, simulation_configs)
        # run one step of the simulation to move from the initial state but not reach the fields (so they are still moving)
        simulation.random_assign_and_simulate(protecting_count, 1)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, TEST_STEP)

        self.assert_no_drones_without_assignment(simulation, DroneState.MOVING_TO_FIELD)

    @pytest.mark.dependency(depends=["generated_adaptations/tests/test_generic.py::TestAdapt::test_no_repeated_assignments"], scope='session')
    @pytest.mark.parametrize("seed,previously_protecting", [(0, "0/8"), (1, "5/8"), (2, "8/8")])
    def test_not_all_drones_are_idle(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        protecting_count, simulation = self.initialize(adaptation_config, previously_protecting, seed, simulation_class, simulation_configs)
        # run a few steps of the simulation to move from the initial state
        simulation.random_assign_and_simulate(protecting_count, STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, TEST_STEP)

        # count idle drones
        idle_drones = sum(1 for group_id in simulation.assignments.values() if group_id == "idle")

        if idle_drones == len(simulation.drones):
            fail(f'All {len(simulation.drones)} drones were assigned to the "idle" group, no drones were assigned to protect fields.')

    @pytest.mark.parametrize("seed,previously_protecting", [(1, "5/8"), (2, "8/8")])
    def test_no_user_constraints_violated(self, adaptation_config, simulation_class, simulation_configs, seed, previously_protecting):
        protecting_count, simulation = self.initialize(adaptation_config, previously_protecting, seed, simulation_class, simulation_configs)
        # run a few steps of the simulation to move from the initial state
        simulation.random_assign_and_simulate(protecting_count, STEPS)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, TEST_STEP)
        simulation.check_user_constraints()

        assert_no_user_constraints_violated(simulation.assignment_errors)
