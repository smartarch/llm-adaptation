from pathlib import Path
from typing import TypeVar

import pytest

from base_classes.adaptation import import_adaptation
from base_classes.simulation import ComponentAlreadyAssignedError, AssignmentError, InvalidGroupError, \
    MissingAssignmentError, UserConstraintError
from utils import read_configs, nested_update

T = TypeVar('T', bound=AssignmentError)


class TestConfiguration:
    """Checks that test parameters are set correctly."""

    @pytest.mark.dependency()
    def test_example_is_correct(self, example):
        assert example in ("farm", "dragon")

    @pytest.mark.dependency(depends=["TestConfiguration::test_example_is_correct"])
    def test_adaptation_exists(self, example, adaptation_name):
        path = Path(f"generated_adaptations/{example}/{adaptation_name}.py")
        assert path.exists(), f"{path.resolve()} does not exist"


def filter_errors(errors: list[AssignmentError], error_class: type[T]) -> list[T]:
    return [error for error in errors if isinstance(error, error_class)]


def assert_no_repeated_assignments(assignment_errors):
    repeatedly_assigned = filter_errors(assignment_errors, ComponentAlreadyAssignedError)
    assert repeatedly_assigned == [], f"{len(repeatedly_assigned)} components were assigned more than once. Each component must be assigned exactly once."


def assert_no_invalid_groups(assignment_errors):
    invalid_groups = filter_errors(assignment_errors, InvalidGroupError)
    assert invalid_groups == [], f"Invalid groups: {[group.group_id for group in invalid_groups]}."


def assert_no_missing_assignments(assignment_errors):
    missing_assignments = filter_errors(assignment_errors, MissingAssignmentError)
    assert missing_assignments == [], f"{missing_assignments} components have not been assigned to a group. Each component must be assigned exactly once."


def assert_no_user_constraints_violated(assignment_errors):
    user_constraint_violations = filter_errors(assignment_errors, UserConstraintError)
    assert user_constraint_violations == [], f"User constraints were violated: " + ", ".join([error.message for error in user_constraint_violations])


@pytest.mark.dependency(depends=["TestConfiguration::test_adaptation_exists"])
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

        assert simulation.assignment_errors == [], f"There were {len(simulation.assignment_errors)} assignment errors: {[error.message for error in simulation.assignment_errors]}"

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
