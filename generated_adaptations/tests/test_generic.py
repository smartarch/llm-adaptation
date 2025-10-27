import importlib
import itertools
import sys
import traceback
from pathlib import Path
from typing import TypeVar

import pytest

from DSL.dsl_utils import Situation
from base_classes.adaptation import import_adaptation
from base_classes.simulation import ComponentAlreadyAssignedError, AssignmentError, InvalidGroupError, \
    MissingAssignmentError, UserConstraintError, Simulation
from generated_adaptations.generator_utils import adaptation_class_name, adaptation_class, simulation_configs, \
    adaptation_config
from utils import read_configs, nested_update, set_random_seed

T = TypeVar('T', bound=AssignmentError)


def fail_without_traceback(message: str):
    """Fail without a traceback. It is recommended to use this instead of simple `assert` statements in tests."""
    pytest.fail(message, pytrace=False)


class TestConfiguration:
    """Checks that test parameters are set correctly."""

    @pytest.mark.dependency()
    def test_example_is_correct(self, example):
        assert example in ("farm", "dragon")

    @pytest.mark.dependency(depends=["TestConfiguration::test_example_is_correct"])
    def test_adaptation_exists(self, example, variant, adaptation_name):
        path = Path(f"generated_adaptations/{example}/{variant}/{adaptation_name}.py")
        assert path.exists(), f"{path.resolve()} does not exist"

    @pytest.mark.dependency(depends=["TestConfiguration::test_adaptation_exists"])
    def test_adaptation_class_is_correct(self, example, variant, adaptation_name):
        module = importlib.import_module(f"generated_adaptations.{example}.{variant}.{adaptation_name.replace('/', '.')}")
        class_name = adaptation_class_name(example)
        if not hasattr(module, class_name):
            fail_without_traceback(f"The strategy must be a class named `{class_name}`.")
        clazz = getattr(module, class_name)
        base_class, base_class_path = adaptation_class(example)
        if not issubclass(clazz, base_class):
            fail_without_traceback(f"The strategy (class `{class_name}`) must be derived from `{base_class_path}`.")
        if clazz.__abstractmethods__:
            fail_without_traceback(f"The strategy must implement all abstract methods of `{base_class.__name__}`: {', '.join(base_class.__abstractmethods__)}. Your strategy (class `{class_name}`) is missing: {', '.join(clazz.__abstractmethods__)}.")


def filter_errors(errors: list[AssignmentError], error_class: type[T]) -> list[T]:
    return [error for error in errors if isinstance(error, error_class)]


def assert_no_assignment_errors(assignment_errors, fail=fail_without_traceback):
    if assignment_errors:
        fail(len(assignment_errors))  # type: ignore


def assert_no_repeated_assignments(assignment_errors, fail=fail_without_traceback):
    repeatedly_assigned = filter_errors(assignment_errors, ComponentAlreadyAssignedError)
    if repeatedly_assigned:
        message = ""
        for assignment, group in itertools.groupby(repeatedly_assigned, key=lambda e: e.assignment):
            message += f"In '{assignment}', {len(list(group))} components were assigned more than once. "
        fail(message + "Each component must be assigned exactly once.")


def assert_no_invalid_groups(assignment_errors, fail=fail_without_traceback):
    invalid_groups = filter_errors(assignment_errors, InvalidGroupError)
    if invalid_groups:
        fail(f"Invalid groups: {[group.group_id for group in invalid_groups]}.")


def assert_no_missing_assignments(assignment_errors, fail=fail_without_traceback):
    missing_assignments = filter_errors(assignment_errors, MissingAssignmentError)
    if missing_assignments:
        components = [str(error.component) for error in missing_assignments]
        fail(f"The following components have not been assigned to a group: {', '.join(components)}. Each component must be assigned exactly once.")


def assert_no_functional_constraints_violated(assignment_errors, fail=fail_without_traceback):
    functional_constraint_violations = filter_errors(assignment_errors, UserConstraintError)
    if functional_constraint_violations:
        fail("\n\n".join([error.message for error in functional_constraint_violations]))


@pytest.mark.dependency(depends=["TestConfiguration::test_adaptation_class_is_correct"])
class TestAdapt:

    @staticmethod
    def pytest_generate_tests(metafunc):
        # load the configs
        example = metafunc.config.getoption("example")
        variant = metafunc.config.getoption("variant")
        adaptation_name = metafunc.config.getoption("adaptation_name")
        tests = metafunc.config.getoption("tests")
        config = read_configs(simulation_configs(example, tests == "all"))
        config = nested_update(config, adaptation_config(adaptation_name, example, variant))

        situations_config = config.get("adaptation_params", {}).get("prompt_template_params", {}).get("situations", {})
        situations = []
        for name, situation_config in situations_config.items():
            situation = Situation(name=name, config=config)
            if "seed" in situation_config:
                situation.seed = situation_config["seed"]
            if "steps" in situation_config:
                situation.steps = situation_config["steps"]
            else:
                situation.steps = config["steps"]
            if "arrange" in situation_config:
                module, func_name = situation_config["arrange"].rsplit(".", 1)
                arrange_module = importlib.import_module(module)
                arrange_func = getattr(arrange_module, func_name)
                situation.arrange = arrange_func
                if "params" in situation_config:
                    situation.params = situation_config["params"]
            situations.append(situation)
        metafunc.parametrize("situation", situations, ids=str)

    @staticmethod
    def init_simulation(situation, simulation_class) -> Simulation:
        set_random_seed(situation.seed)
        adaptation = import_adaptation(situation.config)
        simulation = simulation_class(adaptation.adapt, situation.config)
        adaptation.init(simulation)

        if situation.arrange:
            simulation = situation.arrange(simulation, **situation.params)
        return simulation

    @staticmethod
    def run_simulation_with_assert_after_each_adapt(simulation, steps, assert_after_each_adapt, immediate=True, message=None):
        failures = []
        if immediate:
            fail = fail_without_traceback
        else:  # collect failures instead of failing immediately
            def add_failure(message):
                failures.append(message)
            fail = add_failure

        error: str | None = None

        def assignment_errors_handler(errors: list[AssignmentError]):
            if error:  # we cannot use `fail` within `except` block (in simulation_step), because it does not work correctly, so we store the error in adapt_exception_handler and handle it here
                fail_without_traceback(error)
            assert_after_each_adapt(errors, fail=fail)

        def adapt_exception_handler(e: Exception):
            nonlocal error
            tb_frames = traceback.extract_tb(sys.exc_info()[2])
            error = f"{type(e).__name__} on line {tb_frames[-1].lineno} in {tb_frames[-1].name}: {e}"

        simulation.assignment_errors_handler = assignment_errors_handler
        simulation.adapt_exception_handler = adapt_exception_handler
        simulation.run_simulation(steps)

        if not immediate:
            if failures:
                if message:
                    fail_without_traceback(message(failures))
                else:
                    fail_without_traceback("\n\n".join(failures))

    def test_no_assignment_errors(self, situation, simulation_class):
        simulation = self.init_simulation(situation, simulation_class)
        steps = situation.steps
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_assignment_errors, immediate=False, message=lambda failures: f"There were {sum(failures)} assignment errors in total.")

    def test_no_repeated_assignments(self, situation, simulation_class):
        simulation = self.init_simulation(situation, simulation_class)
        steps = situation.steps
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_repeated_assignments)

    def test_no_invalid_groups(self, situation, simulation_class):
        simulation = self.init_simulation(situation, simulation_class)
        steps = situation.steps
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_invalid_groups)

    def test_all_assigned(self, situation, simulation_class):
        simulation = self.init_simulation(situation, simulation_class)
        steps = situation.steps
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_missing_assignments)

    def test_no_functional_constraints_violated(self, situation, simulation_class):
        simulation = self.init_simulation(situation, simulation_class)
        steps = situation.steps
        self.run_simulation_with_assert_after_each_adapt(simulation, steps, assert_no_functional_constraints_violated, immediate=False)

    def test_no_functional_constraints_violated_at_the_end(self, situation, simulation_class):
        simulation = self.init_simulation(situation, simulation_class)
        steps = situation.steps
        simulation.run_simulation(steps)
        assert_no_functional_constraints_violated(simulation.assignment_errors)
