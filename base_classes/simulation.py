import abc
import sys
from collections import defaultdict
from typing import Callable, Optional
import traceback

from DSL.dsl_utils import DSLConfiguration, UserConstraint, EnsembleInstance, LongTermConstraintViolations
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
    def __init__(self, message: str):
        super().__init__(message)


class LongTermConstraintError(AssignmentError):
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

        self.current_assignment: str | None = None  # name of the assignment method currently being executed, if any
        self.assignments: dict[Component, str] = {}
        self.assignment_errors: list[AssignmentError] = []
        self.step: Optional[int] = None
        self.adapt_every = self.config.get("adaptation_params", {}).get("adapt_every", 1)
        self.constraints_violations: dict[UserConstraint, LongTermConstraintViolations] = defaultdict(LongTermConstraintViolations)

        self.dsl_config = DSLConfiguration(config.get("adaptation_params", {}).get("prompt_template_params", {}))

    def run_simulation(self, steps: int):
        step = 0
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
        self.reset_assignments()
        self._check_long_term_constraint_violations()

    def simulation_step(self, step):
        self.reset_assignments()
        if self.should_adapt(step):
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

    def should_adapt(self, step) -> bool:
        """Adaptation should be performed at this step. Set to False, for example, when there are no adaptable components left."""
        return (step - 1) % self.adapt_every == 0

    def add_visualizer(self, visualizer):
        self.visualizer = visualizer

    def add_stats(self, stats):
        self.stats = stats

    def get_globals(self):
        """Returns the classes and global functions as a dictionary that can be used in `eval`."""
        return {
            "environment": self,
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
        self.check_user_constraints()

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
        for assignment_name in self.dsl_config.load_assignment_names():
            components = self.dsl_config.load_components_for_assignment(self, assignment_name)
            ensemble_instances = self.dsl_config.load_ensemble_instances_for_assignment(self, assignment_name)
            resolved_ensembles = self._resolve_ensembles(ensemble_instances)

            for constraint in self.dsl_config.load_constraints(self, assignment_name, resolved_ensembles, components):
                self._check_user_constraint(constraint)

    def _check_user_constraint(self, constraint: UserConstraint):
        # check the constraint for each ensemble
        def check_constraint(*reason_args):
            self.constraints_violations[constraint].constraint = constraint
            self.constraints_violations[constraint].occurrences += 1
            if not constraint.constraint(*reason_args):
                if constraint.occurrence == "always":
                    self.append_assignment_error(UserConstraintError(constraint.reason(*reason_args)))
                else:
                    self.constraints_violations[constraint].violations += 1
                    self.constraints_violations[constraint].reason = constraint.reason(*reason_args)

        if constraint.foreach:
            for resolved_ensemble in self._resolve_ensembles(constraint.relevant_ensembles):
                check_constraint(resolved_ensemble)
        else:
            check_constraint()

    def _check_long_term_constraint_violations(self):
        for constraint, violations in self.constraints_violations.items():
            self._check_long_term_constraint_violation(constraint.occurrence, violations)
        print("Long-term constraint violations:", file=sys.stderr)
        for error in self.assignment_errors:
            print(error.message, file=sys.stderr)

    def _check_long_term_constraint_violation(self, occurrence, constraint_violations: LongTermConstraintViolations):
        violations = constraint_violations.violations
        total_tested = constraint_violations.occurrences
        if occurrence == "always":  # should never be violated
            self.append_assignment_error(LongTermConstraintError(f"Long-term constraint '{constraint_violations.reason}' was violated {violations} times out of {total_tested} tested."))
        elif occurrence == "once":  # should hold at least once -> violations <= steps - 1
            if violations > total_tested - 1:
                self.append_assignment_error(LongTermConstraintError(f"Long-term constraint '{constraint_violations.reason}' should hold at least once, but was violated in every step."))
        elif isinstance(occurrence, float):  # should hold at least this fraction of the time
            if violations / total_tested > (1 - occurrence):
                self.append_assignment_error(LongTermConstraintError(
                    f"Long-term constraint '{constraint_violations.reason}' should hold at least {occurrence:.1%} of the time, "
                    f"but was violated {violations} times out of {total_tested} tested ({violations / total_tested:.1%})."
                ))

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
