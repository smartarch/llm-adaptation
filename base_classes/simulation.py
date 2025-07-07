import abc
import sys
from typing import Callable, Optional
import traceback

from DSL.dsl_utils import DSLConfiguration
from base_classes.components import Component
from base_classes.ensembles import Ensemble


class AssignmentError(Exception):

    @property
    def message(self):
        return self.args[0]


class ComponentAlreadyAssignedError(AssignmentError):
    def __init__(self, component: Component):
        self.component = component
        super().__init__(f"Component assigned into multiple groups: {component}")


class InvalidGroupError(AssignmentError):
    def __init__(self, group_id):
        self.group_id = group_id
        super().__init__(f"Invalid group: {group_id}")


class UnknownComponentError(AssignmentError):
    def __init__(self, component_id: str):
        super().__init__(f"Unknown component: {component_id}")


class MissingAssignmentError(AssignmentError):
    def __init__(self, component: Component):
        self.component = component
        super().__init__(f"Missing assignment for: {component}")


class UserConstraintError(AssignmentError):
    def __init__(self, message: str):
        super().__init__(message)


class Simulation(abc.ABC):

    def __init__(self, adapt: Callable[["Simulation", int], None], config: dict):
        self.config = config
        self.adapt = adapt
        self.components: list[Component] = []
        self.beyond_control_components: list[Component] = []

        self.visualizer = None
        self.stats = None

        self.assignments: dict[Component, str] = {}
        self.assignment_errors: list[AssignmentError] = []
        self.step: Optional[int] = None

        self.dsl_config = DSLConfiguration(config.get("adaptation_params", {}).get("prompt_template_params", {}))

    def run_simulation(self, steps: int):
        for step in range(1, steps + 1):
            print(f"Step: {step}")
            self.step = step

            self.simulation_step(step)

            if self.stats:
                self.stats.write_row(step)
            if self.visualizer:
                self.visualizer.drawComponents(step)

            if self.should_stop():
                break

    def simulation_step(self, step):
        self.reset_assignments()
        if self.should_adapt():
            try:
                self.adapt(self, step)
            except Exception as error:
                print(traceback.format_exc(), file=sys.stderr)
        self._apply_assignments()

        for component in self.components + self.beyond_control_components:
            component.actuate()

    def should_stop(self):
        """Simulation should stop."""
        return False

    def should_adapt(self) -> bool:
        """Adaptation should be performed at this step. Set to False, for example, when there are no adaptable components left."""
        return True

    def add_visualizer(self, visualizer):
        self.visualizer = visualizer

    def add_stats(self, stats):
        self.stats = stats

    @staticmethod
    def get_globals():
        """Returns the classes and global functions as a dictionary that can be used in `eval`."""
        return {}

    def assign_group(self, component: Component, group_id: str) -> AssignmentError | None:
        try:
            self._check_group(component, group_id)
            self.assignments[component] = group_id
            return None
        except AssignmentError as error:
            self.append_assignment_error(error)
            return error

    def append_assignment_error(self, error):
        print("Before retry:", error.message)
        self.assignment_errors.append(error)

    @abc.abstractmethod
    def _check_group(self, component: Component, group_id: str):
        """Checks whether a component can be assigned to a group. Should throw an error if the assignment is invalid."""
        pass

    def _apply_assignments(self):
        """Apply the group assignments (self.assignments)."""
        self.check_user_constraints()

        for error in self.assignment_errors:
            print("Error in final assignment:", error.message)
            print(error.message, file=sys.stderr)

        for component, group_id in self.assignments.items():
            self._assign_group(component, group_id)

    def check_missing_assignments(self, components_to_be_assigned):
        if len(self.assignments) < len(components_to_be_assigned):
            for component in components_to_be_assigned:
                if component not in self.assignments:
                    self.append_assignment_error(MissingAssignmentError(component))

    def check_user_constraints(self):
        for assignment_config in self.dsl_config.load_assignments():
            for constraint_config in self.dsl_config.load_constraints_for_assignment(self, assignment_config):
                self._check_user_constraint(**constraint_config)

    # TODO: the attribute names here depend on the dict keys returned from `dsl_utils.load_constraints_for_assignment`. We should probably replace the dict with a proper class.
    def _check_user_constraint(self, constraint, ensembles, reason):
        ensemble_instances = []
        # load members for each ensemble
        for ensemble_config in ensembles:
            members = [c for c, e in self.assignments.items() if e == ensemble_config["name"]]
            ensemble_instances.append(Ensemble(ensemble_config, members))
        # check the constraint for each ensemble
        for ensemble in ensemble_instances:
            if not constraint(ensemble):
                reason = reason(ensemble)
                self.append_assignment_error(UserConstraintError(reason))

    @abc.abstractmethod
    def _assign_group(self, component: Component, group_id: str):
        pass

    def reset_assignments(self):
        self.assignments = {}
        self.assignment_errors = []
