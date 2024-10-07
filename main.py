import os
import random
import sys
from datetime import datetime

from langchain.globals import set_verbose, set_debug

from base_classes.adaptation import import_adaptation
from plots import draw_plots
from simulation import SmartFarmSimulation
from stats import Stats
from utils import read_yaml, Logger
from visualizer import Visualizer


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(), override=True)  # take environment variables from .env

# set_verbose(True)
# set_debug(True)

config_file = sys.argv[1] if len(sys.argv) > 1 else "configs/config.yaml"

config = read_yaml(config_file)
name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-") + config["name"]
sys.stdout = Logger(f"logs/{name}")


adaptation = import_adaptation(config)
simulation = SmartFarmSimulation(adaptation.adapt, config)

visualizer = Visualizer(simulation)
simulation.add_visualizer(visualizer)
visualizer.drawFields()
stats = Stats(simulation, f"logs/{name}.csv")
simulation.add_stats(stats)
stats.write_header()

print("\nRunning simulation...\n")
simulation.run_simulation(200)
print("\nSimulation done")

print("\nStatistics:")
for label, value in zip(stats.global_stats(None, header=True), stats.global_stats(None)):
    print(f"{label}: {value}")
print("\nSaving plot...")
draw_plots(f"logs/{name}")
print("\nSaving animation...")
os.makedirs("animations", exist_ok=True)
visualizer.createAnimation(f"logs/{name}.gif")
print("Done")
