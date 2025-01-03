import argparse
import os
import sys
from datetime import datetime

from langchain.globals import set_verbose, set_debug

from base_classes.adaptation import import_adaptation
from plots import draw_plots
from simulation import SmartFarmSimulation
from stats import Stats
from utils import read_configs, Logger, print_config
from visualizer import Visualizer


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(), override=True)  # take environment variables from .env

parser = argparse.ArgumentParser()
parser.add_argument("--animation", "-a", default=False, action="store_true")
parser.add_argument("config_files", type=str, nargs='+', help="Configuration yaml files.", default=["configs/config.yaml", "configs/fake.yaml"])
parser.add_argument('--episode', '-e', type=int, help="Episode (iteration) number. It is used as part of the log file name.")
parser.add_argument('--seed', '-s', type=int, help="Seed for random number generator.")
args = parser.parse_args()

# set_verbose(True)
# set_debug(True)

config = read_configs(args.config_files)
name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-") + config["name"]
if args.episode is not None:
    name = f"{args.episode:03}-{name}"
log_dir = config["log_dir"]
sys.stdout = Logger(f"{log_dir}/{name}.ansi")
sys.stderr = Logger(f"{log_dir}/{name}.err", sys.stderr, create_on_first_write=True)

if args.seed is not None:
    from keras.utils import set_random_seed
    set_random_seed(args.seed)

config["log_dir"] = log_dir
config["log_file_name"] = name
config["log_file_path"] = f"{log_dir}/{name}.ansi"
print_config(config)

adaptation = import_adaptation(config)
simulation = SmartFarmSimulation(adaptation.adapt, config)
adaptation.init(simulation)

if args.animation:
    visualizer = Visualizer(simulation)
    simulation.add_visualizer(visualizer)
    visualizer.drawFields()
stats = Stats(simulation, f"{log_dir}/{name}.csv")
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
draw_plots(f"{log_dir}/{name}")
print("Done")

if args.animation:
    print("\nSaving animation... ", end="")
    os.makedirs("animations", exist_ok=True)
    # noinspection PyUnboundLocalVariable
    visualizer.createAnimation(f"{log_dir}/{name}.gif")
    print("Done")
