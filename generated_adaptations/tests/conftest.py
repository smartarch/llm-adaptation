import random

import pytest

from generated_adaptations import generator_utils


# set random seed for tests
random.seed(42)


def pytest_addoption(parser):
    parser.addoption("--example", action="store")
    parser.addoption("--adaptation_name", action="store")


@pytest.fixture(scope="session")
def adaptation_name(pytestconfig):
    return pytestconfig.getoption("adaptation_name")


@pytest.fixture(scope="session")
def example(pytestconfig):
    return pytestconfig.getoption("example")


@pytest.fixture(scope="session")
def simulation_class(example):
    return generator_utils.simulation_class(example)


@pytest.fixture(scope="session")
def simulation_configs(example):
    return generator_utils.simulation_configs(example)


@pytest.fixture(scope="session")
def adaptation_config(adaptation_name, example):
    return generator_utils.adaptation_config(adaptation_name, example)


@pytest.fixture(autouse=True)
def reset_component_counters(example):
    """Automatically reset component counters before each test."""
    return generator_utils.reset_component_counters(example)


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

    # add names to the test parameters
    if hasattr(item, "callspec"):
        params = dict(item.callspec.params)
        params.pop("seed")
        if params:
            report.nodeid = report.nodeid.split("[")[0]
            report.nodeid += f"[{', '.join(f'{k}={v}' for k, v in params.items())}]"

    # # replace the test name with its docstring
    # test_fn = item.obj
    # docstring = getattr(test_fn, '__doc__')
    # if docstring:
    #     report.nodeid = docstring
