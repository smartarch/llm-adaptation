from pathlib import Path
from typing import TypeVar

import pytest

from base_classes.adaptation import import_adaptation
from base_classes.simulation import ComponentAlreadyAssignedError, AssignmentError, InvalidGroupError
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

    @staticmethod
    def filter_errors(errors: list[AssignmentError], error_class: type[T]) -> list[T]:
        return [error for error in errors if isinstance(error, error_class)]

    @staticmethod
    def filter_assignment_errors_by_type(assignment_errors, error_type):
        return list(filter(lambda error: isinstance(error, error_type), assignment_errors))

    def test_no_repeated_assignments(self, adaptation_config, simulation_class, simulation_configs):
        simulation = self.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # run one step
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        repeatedly_assigned = self.filter_errors(simulation.assignment_errors, ComponentAlreadyAssignedError)
        assert repeatedly_assigned == [], f"{len(repeatedly_assigned)} components were assigned more than once. Each component must be assigned exactly once."

    def test_no_invalid_groups(self, adaptation_config, simulation_class, simulation_configs):
        simulation = self.init_simulation(adaptation_config, simulation_class, simulation_configs)

        # run one step 
        simulation.reset_assignments()
        simulation.adapt(simulation, 1)

        invalid_groups = self.filter_errors(simulation.assignment_errors, InvalidGroupError)
        assert invalid_groups == [], f"Invalid groups: {[group.group_id for group in invalid_groups]}."

    # TODO: test_all_assigned -- it is necessary to detect which components should be assigned (from the DSL)
