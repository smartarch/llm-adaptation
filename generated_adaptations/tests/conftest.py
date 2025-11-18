from collections import defaultdict

import pytest

from generated_adaptations import generator_utils


def pytest_addoption(parser):
    parser.addoption("--example", action="store")
    parser.addoption("--variant", action="store", default="default")
    parser.addoption("--adaptation_name", action="store")
    parser.addoption("--tests", choices=["system", "all", "functional"], required=True)


def load_constraints(tests):
    return tests in ("all", "functional")

@pytest.fixture(scope="session")
def adaptation_name(pytestconfig):
    return pytestconfig.getoption("adaptation_name")


@pytest.fixture(scope="session")
def example(pytestconfig):
    return pytestconfig.getoption("example")


@pytest.fixture(scope="session")
def variant(pytestconfig):
    return pytestconfig.getoption("variant")


@pytest.fixture(scope="session")
def tests(pytestconfig):
    return pytestconfig.getoption("tests")


@pytest.fixture(scope="session")
def simulation_class(example):
    return generator_utils.simulation_class(example)


@pytest.fixture(scope="session")
def simulation_configs(example, tests):
    return generator_utils.simulation_configs(example, constraints=load_constraints(tests))


@pytest.fixture(scope="session")
def adaptation_config(adaptation_name, example, variant):
    return generator_utils.adaptation_config(adaptation_name, example, variant)


@pytest.fixture(autouse=True)
def reset_component_counters(example):
    """Automatically reset component counters before each test."""
    try:
        generator_utils.reset_component_counters(example)
    except ValueError:
        pass


def pytest_collection_modifyitems(items):
    # Move test_generic.py items to the front of the test queue before use-case-specific tests
    generic_items = [item for item in items if "test_generic.py" in str(item.fspath)]
    other_items = [item for item in items if "test_generic.py" not in str(item.fspath)]
    items[:] = generic_items + other_items


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    # remove file name from nodeid
    report.nodeid = report.nodeid.removeprefix(report.fspath + "::")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    results = defaultdict(lambda: defaultdict(list))

    # Collect situations grouped by test name and outcome
    for outcome in ["passed", "failed"]:
        for report in terminalreporter.stats.get(outcome, []):
            if report.nodeid.startswith("TestConfiguration"):
                continue
            parts = report.nodeid.split("[")
            test_name = parts[0]
            situation = parts[1][:-1]
            results[test_name][outcome].append(situation)

    # Print formatted results
    terminalreporter.section("Test Results", sep="=")
    for test_name, outcomes in results.items():
        terminalreporter.write(f"{test_name}:")
        if "failed" in outcomes:
            failed_situations = ", ".join(outcomes["failed"])
            terminalreporter.write(f"\n - failed for: {failed_situations}")
        if "passed" in outcomes:
            passed_situations = ", ".join(outcomes["passed"])
            terminalreporter.write(f"\n - passed for: {passed_situations}")
        terminalreporter.write("\n")

    # Clear the "short test summary info" section
    terminalreporter.reportchars = []
