import argparse
import os
import random
import sys
from datetime import datetime

from langchain.globals import set_verbose, set_debug

from base_classes.adaptation import import_adaptation
from plots import draw_plots
from simulation import SmartFarmSimulation
from stats import Stats
from utils import read_configs, Logger
from visualizer import Visualizer


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(), override=True)  # take environment variables from .env

parser = argparse.ArgumentParser()
parser.add_argument("--animation", "-a", default=False, action="store_true")
parser.add_argument("--log_dir", "-l", type=str, default="logs")
parser.add_argument("config_files", type=str, nargs='+', help="Configuration yaml files.", default=["configs/config.yaml", "configs/fake.yaml"])
args = parser.parse_args()

# set_verbose(True)
# set_debug(True)

config = read_configs(args.config_files)
name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-") + config["name"]
sys.stdout = Logger(f"{args.log_dir}/{name}")


adaptation = import_adaptation(config)
simulation = SmartFarmSimulation(adaptation.adapt, config)

if args.animation:
    visualizer = Visualizer(simulation)
    simulation.add_visualizer(visualizer)
    visualizer.drawFields()
stats = Stats(simulation, f"{args.log_dir}/{name}.csv")
simulation.add_stats(stats)
stats.write_header()

print("\nRunning simulation...\n")
simulation.run_simulation(300)
print("\nSimulation done")

adaptation.end(simulation)

print("\nStatistics:")
for label, value in zip(stats.global_stats(None, header=True), stats.global_stats(None)):
    print(f"{label}: {value}")
stats.close_file()

print("\nSaving plot... ", end="")
draw_plots(f"{args.log_dir}/{name}")
print("Done")

if args.animation:
    print("\nSaving animation... ", end="")
    os.makedirs("animations", exist_ok=True)
    # noinspection PyUnboundLocalVariable
    visualizer.createAnimation(f"{args.log_dir}/{name}.gif")
    print("Done")
