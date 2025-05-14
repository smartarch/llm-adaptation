import random

import pytest


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
    if example == "farm":
        from farm.simulation import SmartFarmSimulation as Simulation
    elif example == "dragon":
        from dragon.simulation import DragonHuntSimulation as Simulation
    else:
        raise ValueError(f"Unknown example: {example}")
    return Simulation


@pytest.fixture(scope="session")
def simulation_configs(example):
    if example == "farm":
        configs = ["farm/configs/default.yaml", "generated_adaptations/configs/generated.yaml", "farm/configs/config_no_battery.yaml"]
    elif example == "dragon":
        configs = ["dragon/configs/default.yaml", "generated_adaptations/configs/generated.yaml"]
    else:
        raise ValueError(f"Unknown example: {example}")
    return configs


@pytest.fixture(scope="session")
def adaptation_config(adaptation_name, example):
    if example == "farm":
        class_name = "SmartFarmAdaptation"
    elif example == "dragon":
        class_name = "SmartAdaptation"
    else:
        raise ValueError(f"Unknown example: {example}")

    return {
        "name": adaptation_name,
        "log_dir.append": f"/{adaptation_name}",
        "adaptation_name": f"generated_adaptations.{example}.{adaptation_name.replace('/', '.')}.{class_name}",
    }


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
