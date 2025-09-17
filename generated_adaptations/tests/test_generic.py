import importlib
import itertools
import sys
import traceback
from pathlib import Path
from typing import TypeVar

import pytest

from base_classes.adaptation import import_adaptation
from base_classes.simulation import ComponentAlreadyAssignedError, AssignmentError, InvalidGroupError, \
    MissingAssignmentError, UserConstraintError, Simulation, LongTermConstraintError
from generated_adaptations.generator_utils import adaptation_class_name, adaptation_class
from utils import read_configs, nested_update

T = TypeVar('T', bound=AssignmentError)


def fail(message: str):
    """Fail without a traceback. It is recommended to use this instead of simple `assert` statements in tests."""
    pytest.fail(message, pytrace=False)


class TestConfiguration:
    """Checks that test parameters are set correctly."""

    @pytest.mark.dependency()
    def test_example_is_correct(self, example):
        assert example in ("farm", "dragon")

    @pytest.mark.dependency(depends=["TestConfiguration::test_example_is_correct"])
    def test_adaptation_exists(self, example, adaptation_name):
        path = Path(f"generated_adaptations/{example}/{adaptation_name}.py")
        assert path.exists(), f"{path.resolve()} does not exist"

    @pytest.mark.dependency(depends=["TestConfiguration::test_adaptation_exists"])
    def test_adaptation_class_is_correct(self, example, adaptation_name):
        module = importlib.import_module(f"generated_adaptations.{example}.{adaptation_name.replace('/', '.')}")
        class_name = adaptation_class_name(example)
        if not hasattr(module, class_name):
            fail(f"The strategy must be a class named `{class_name}`.")
        clazz = getattr(module, class_name)
        base_class, base_class_path = adaptation_class(example)
        if not issubclass(clazz, base_class):
            fail(f"The strategy (class `{class_name}`) must be derived from `{base_class_path}`.")
        if clazz.__abstractmethods__:
            fail(f"The strategy must implement all abstract methods of `{base_class.__name__}`: {', '.join(base_class.__abstractmethods__)}. Your strategy (class `{class_name}`) is missing: {', '.join(clazz.__abstractmethods__)}.")


def filter_errors(errors: list[AssignmentError], error_class: type[T]) -> list[T]:
    return [error for error in errors if isinstance(error, error_class)]


def assert_no_assignment_errors(assignment_errors):
    if assignment_errors:
        fail(f"There were {len(assignment_errors)} assignment errors:\n\n" +
             "\n".join([error.message for error in assignment_errors]))


def assert_no_repeated_assignments(assignment_errors):
    repeatedly_assigned = filter_errors(assignment_errors, ComponentAlreadyAssignedError)
    if repeatedly_assigned:
        message = ""
        for assignment, group in itertools.groupby(repeatedly_assigned, key=lambda e: e.assignment):
            message += f"In '{assignment}', {len(list(group))} components were assigned more than once. "
        fail(message + "Each component must be assigned exactly once.")


def assert_no_invalid_groups(assignment_errors):
    invalid_groups = filter_errors(assignment_errors, InvalidGroupError)
    if invalid_groups:
        fail(f"Invalid groups: {[group.group_id for group in invalid_groups]}.")


def assert_no_missing_assignments(assignment_errors):
    missing_assignments = filter_errors(assignment_errors, MissingAssignmentError)
    if missing_assignments:
        components = [str(error.component) for error in missing_assignments]
        fail(f"The following components have not been assigned to a group: {', '.join(components)}. Each component must be assigned exactly once.")


def assert_no_user_constraints_violated(assignment_errors):
    user_constraint_violations = filter_errors(assignment_errors, UserConstraintError)
    if user_constraint_violations:
        fail("User constraints violated.\n\n" +
             "\n".join([error.message for error in user_constraint_violations]))


def assert_no_long_term_constraints_violated(assignment_errors):
    long_term_constraint_violations = filter_errors(assignment_errors, LongTermConstraintError)
    if long_term_constraint_violations:
        fail("Long-term constraints violated.\n\n" +
             "\n".join([error.message for error in long_term_constraint_violations]))


@pytest.mark.dependency(depends=["TestConfiguration::test_adaptation_class_is_correct"])
class TestAdapt:

    @staticmethod
    def init_simulation(adaptation_config, simulation_class, simulation_configs) -> tuple[Simulation, dict]:
        config = read_configs(simulation_configs)
        config = nested_update(config, adaptation_config)
        adaptation = import_adaptation(config)

        simulation = simulation_class(adaptation.adapt, config)
        adaptation.init(simulation)

        return simulation, config

    @staticmethod
    def run_simulation_with_assert_after_each_adapt(simulation, steps, assert_after_each_adapt):
        # this code is based on `simulation.run_simulation` and `simulation.simulation_step`
        for step in range(1, steps + 1):
            simulation.step = step
            simulation.reset_assignments()
            if simulation.should_adapt(step):
                error = None
                try:
                    simulation.adapt(simulation, step)
                except Exception as e:
                    tb_frames = traceback.extract_tb(sys.exc_info()[2])
                    error = f"{type(e).__name__} on line {tb_frames[-1].lineno} in {tb_frames[-1].name}: {e}"
                if error:  # we cannot use `fail` within `except` block, because it does not work correctly
                    fail(error)
                simulation.check_user_constraints()

                assert_after_each_adapt(simulation.assignment_errors)

                simulation._apply_assignments()

            for component in simulation.components + simulation.beyond_control_components:
                component.actuate()

            if simulation.should_stop():
                break

    def test_no_assignment_errors(self, adaptation_config, simulation_class, simulation_configs):
        simulation, config = self.init_simulation(adaptation_config, simulation_class, simulation_configs)
        steps = config["steps"]
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_assignment_errors)

    def test_no_repeated_assignments(self, adaptation_config, simulation_class, simulation_configs):
        simulation, config = self.init_simulation(adaptation_config, simulation_class, simulation_configs)
        steps = config["steps"]
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_repeated_assignments)

    def test_no_invalid_groups(self, adaptation_config, simulation_class, simulation_configs):
        simulation, config = self.init_simulation(adaptation_config, simulation_class, simulation_configs)
        steps = config["steps"]
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_invalid_groups)

    def test_all_assigned(self, adaptation_config, simulation_class, simulation_configs):
        simulation, config = self.init_simulation(adaptation_config, simulation_class, simulation_configs)
        steps = config["steps"]
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_missing_assignments)

    def test_no_user_constraints_violated(self, adaptation_config, simulation_class, simulation_configs):
        simulation, config = self.init_simulation(adaptation_config, simulation_class, simulation_configs)
        steps = config["steps"]
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_user_constraints_violated)

    def test_no_long_term_constraints_violated(self, adaptation_config, simulation_class, simulation_configs):
        simulation, config = self.init_simulation(adaptation_config, simulation_class, simulation_configs)
        steps = config["steps"]
        simulation.run_simulation(steps)
        assert_no_long_term_constraints_violated(simulation.assignment_errors)
