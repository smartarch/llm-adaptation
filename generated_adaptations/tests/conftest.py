import pytest


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
    return {
        "name": adaptation_name,
        "log_dir.append": f"/{adaptation_name}",
        "adaptation_name": f"generated_adaptations.{example}.{adaptation_name}.SmartFarmAdaptation",
    }
