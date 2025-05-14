import abc
import sys
from typing import Callable, Optional

from base_classes.components import Component


class AssignmentError(Exception):

    @property
    def message(self):
        return self.args[0]


class ComponentAlreadyAssignedError(AssignmentError):

    def __init__(self, component: Component):
        self.component = component
        super().__init__(f"Component already assigned: {component}")


class InvalidGroupError(AssignmentError):
    def __init__(self, group_id):
        self.group_id = group_id
        super().__init__(f"Invalid group: {group_id}")


class MissingAssignmentError(AssignmentError):
    def __init__(self, component: Component):
        self.component = component
        super().__init__(f"Missing assignment for: {component}")


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
                print(error, file=sys.stderr)
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

    def assign_group(self, component: Component, group_id: str) -> str | None:
        try:
            self._check_group(component, group_id)
            self.assignments[component] = group_id
            return None
        except AssignmentError as error:
            self.append_assignment_error(error)
            return error.message

    def append_assignment_error(self, error):
        print("Before retry:", error.message)
        self.assignment_errors.append(error)

    @abc.abstractmethod
    def _check_group(self, component: Component, group_id: str):
        """Checks whether a component can be assigned to a group. Should throw an error if the assignment is invalid."""
        pass

    def _apply_assignments(self):
        """Apply the group assignments (self.assignments)."""
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

    @abc.abstractmethod
    def _assign_group(self, component: Component, group_id: str):
        pass

    def reset_assignments(self):
        self.assignments = {}
        self.assignment_errors = []
