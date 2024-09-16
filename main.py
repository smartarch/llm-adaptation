from simulation import SmartFarmSimulation
from utils import read_yaml


def adapt():
    pass


config = read_yaml("config.yaml")

simulation = SmartFarmSimulation(adapt, config)
simulation.run_simulation(100)
