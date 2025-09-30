import abc
import sys
from typing import Any, Callable, Optional
import traceback

from DSL.dsl_utils import DSLConfiguration, EnsembleInstance
from base_classes.components import Component
from base_classes.ensembles import ResolvedEnsemble


class AssignmentError(Exception):

    assignment: str | None = None  # name of the assignment method that caused the error, if any

    def __init__(self, message: str):
        super().__init__(message)

    @property
    def message(self):
        if self.assignment:
            return f"In '{self.assignment}': {self.args[0]}"
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
    pass


class Simulation(abc.ABC):

    def __init__(self, adapt: Callable[["Simulation", int], None], config: dict):
        self.config = config
        self.adapt = adapt
        self.components: list[Component] = []
        self.beyond_control_components: list[Component] = []

        self.visualizer = None
        self.stats = None

        self.current_assignment: str | None = None  # name of the assignment method currently being executed, if any
        self.assignments: dict[Component, str] = {}
        self.assignment_errors: list[AssignmentError] = []
        self.steps: int = config["steps"]
        self.step: Optional[int] = None
        self.adapt_every = self.config.get("adaptation_params", {}).get("adapt_every", 1)

        self.dsl_config = DSLConfiguration(config.get("adaptation_params", {}).get("prompt_template_params", {}))

        self.assignment_constraints = {
            assignment_name: list(self.dsl_config.load_constraints(self, assignment_name))
            for assignment_name in self.dsl_config.load_assignment_names()
        }
        self.global_constraints = list(self.dsl_config.load_constraints(self, None))

    def run_simulation(self, steps=None):
        simulation_steps: int = steps if steps is not None else self.steps  # type: ignore
        for step in range(1, simulation_steps + 1):
            print(f"Step: {step}")
            self.step = step

            self.simulation_step(step)

            if self.stats:
                self.stats.write_row(step)
            if self.visualizer:
                self.visualizer.drawComponents(step)

            if self.should_stop():
                break
        self.reset_assignments()
        self.check_user_constraints_end()

    def simulation_step(self, step):
        self.reset_assignments()
        if self.should_adapt(step):
            try:
                self.adapt(self, step)
            except Exception:
                print(traceback.format_exc(), file=sys.stderr)
        self.check_user_constraints()
        self._apply_assignments()

        self.actuate_components()

    def actuate_components(self):
        for component in self.components + self.beyond_control_components:
            component.actuate()

    def should_stop(self):
        """Simulation should stop."""
        return False

    def should_adapt(self, step) -> bool:
        """Adaptation should be performed at this step. Set to False, for example, when there are no adaptable components left."""
        return (step - 1) % self.adapt_every == 0

    def add_visualizer(self, visualizer):
        self.visualizer = visualizer

    def add_stats(self, stats):
        self.stats = stats

    def get_globals(self) -> dict[str, Any]:
        """Returns the classes and global functions as a dictionary that can be used in `eval`."""
        return {
            "environment": self,
            "MAX": self.steps - (self.step if self.step is not None else 0),  # remaining steps
        }

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
        error.assignment = self.current_assignment
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
        for component in components_to_be_assigned:
            if component not in self.assignments:
                self.append_assignment_error(MissingAssignmentError(component))

    def check_user_constraints(self):
        # per assignment constraints
        for assignment_name, constraints in self.assignment_constraints.items():
            components = self.dsl_config.load_components_for_assignment(self, assignment_name)
            all_components = list(components.values()) + self.beyond_control_components
            ensemble_instances = self.dsl_config.load_ensemble_instances_for_assignment(self, assignment_name)
            resolved_ensembles = self._resolve_ensembles(ensemble_instances)
            for constraint in constraints:
                for violation in constraint.check(self, all_components, resolved_ensembles):
                    self.assignment_errors.append(UserConstraintError(violation))

        # global constraints
        components = self.dsl_config.load_components_for_all_assignments(self)
        all_components = list(components.values()) + self.beyond_control_components
        ensemble_instances = self.dsl_config.load_ensemble_instances_for_all_assignments(self)
        resolved_ensembles = self._resolve_ensembles(ensemble_instances)
        for constraint in self.global_constraints:
            for violation in constraint.check(self, all_components, resolved_ensembles):
                self.assignment_errors.append(UserConstraintError(violation))

    def check_user_constraints_end(self):
        # per assignment constraints
        for assignment_name, constraints in self.assignment_constraints.items():
            components = self.dsl_config.load_components_for_assignment(self, assignment_name)
            all_components = list(components.values()) + self.beyond_control_components
            for constraint in constraints:
                for violation in constraint.check_end(self, all_components):
                    self.assignment_errors.append(UserConstraintError(violation))

        # global constraints
        components = self.dsl_config.load_components_for_all_assignments(self)
        all_components = list(components.values()) + self.beyond_control_components
        for constraint in self.global_constraints:
            for violation in constraint.check_end(self, all_components):
                self.assignment_errors.append(UserConstraintError(violation))

        # print all errors
        if len(self.assignment_errors) > 0:
            print("Long-term constraint violations:", file=sys.stderr)
            for error in self.assignment_errors:
                print(error.message, file=sys.stderr)

    def _resolve_ensembles(self, ensemble_instances: list[EnsembleInstance]):
        resolved_ensembles = []
        # load members for each ensemble
        for ensemble_instance in ensemble_instances:
            members = [c for c, e in self.assignments.items() if e == ensemble_instance.name]
            resolved_ensembles.append(ResolvedEnsemble(ensemble_instance, members))
        return resolved_ensembles

    @abc.abstractmethod
    def _assign_group(self, component: Component, group_id: str):
        pass

    def reset_assignments(self):
        self.assignments = {}
        self.assignment_errors = []
