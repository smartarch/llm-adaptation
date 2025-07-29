import importlib
from pathlib import Path
from typing import TypeVar

import pytest

from base_classes.adaptation import import_adaptation
from base_classes.simulation import ComponentAlreadyAssignedError, AssignmentError, InvalidGroupError, \
    MissingAssignmentError, UserConstraintError
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


def assert_no_repeated_assignments(assignment_errors):
    repeatedly_assigned = filter_errors(assignment_errors, ComponentAlreadyAssignedError)
    if repeatedly_assigned:
        fail(f"{len(repeatedly_assigned)} components were assigned more than once. Each component must be assigned exactly once.")


def assert_no_invalid_groups(assignment_errors):
    invalid_groups = filter_errors(assignment_errors, InvalidGroupError)
    if invalid_groups:
        fail(f"Invalid groups: {[group.group_id for group in invalid_groups]}.")


def assert_no_missing_assignments(assignment_errors):
    missing_assignments = filter_errors(assignment_errors, MissingAssignmentError)
    if missing_assignments:
        fail(f"{missing_assignments} components have not been assigned to a group. Each component must be assigned exactly once.")


def assert_no_user_constraints_violated(assignment_errors):
    user_constraint_violations = filter_errors(assignment_errors, UserConstraintError)
    if user_constraint_violations:
        fail("User constraints violated.\n\n" +
             "\n".join([error.message for error in user_constraint_violations]))


@pytest.mark.dependency(depends=["TestConfiguration::test_adaptation_class_is_correct"])
class TestAdapt:

    @staticmethod
    def init_simulation(adaptation_config, simulation_class, simulation_configs):
        config = read_configs(simulation_configs)
        config = nested_update(config, adaptation_config)
        adaptation = import_adaptation(config)

        simulation = simulation_class(adaptation.adapt, config)
        adaptation.init(simulation)

        return simulation

    def test_no_assignment_errors(self, adaptation_config, simulation_class, simulation_configs):
        simulation = self.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        if simulation.assignment_errors:
            fail(f"There were {len(simulation.assignment_errors)} assignment errors:\n\n" +
                 "\n".join([error.message for error in simulation.assignment_errors]))

    def test_no_repeated_assignments(self, adaptation_config, simulation_class, simulation_configs):
        simulation = self.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        assert_no_repeated_assignments(simulation.assignment_errors)

    def test_no_invalid_groups(self, adaptation_config, simulation_class, simulation_configs):
        simulation = self.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        assert_no_invalid_groups(simulation.assignment_errors)

    def test_all_assigned(self, adaptation_config, simulation_class, simulation_configs):
        simulation = self.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        assert_no_missing_assignments(simulation.assignment_errors)

    def test_no_user_constraints_violated(self, adaptation_config, simulation_class, simulation_configs):
        simulation = self.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # adapt once
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)
        simulation.check_user_constraints()

        assert_no_user_constraints_violated(simulation.assignment_errors)
