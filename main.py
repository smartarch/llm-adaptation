import os

from simulation import SmartFarmSimulation
from utils import read_yaml
from visualizer import Visualizer


def adapt():
    pass


config = read_yaml("config.yaml")

simulation = SmartFarmSimulation(adapt, config)

visualizer = Visualizer(simulation)
simulation.add_visualizer(visualizer)
visualizer.drawFields()

simulation.run_simulation(100)

print("Saving animation...")
os.makedirs("animations", exist_ok=True)
visualizer.createAnimation(f"animations/output.gif")
print("Done")
