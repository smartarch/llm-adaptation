import argparse
import json
import os
import sys
from datetime import datetime

from base_classes.adaptation import import_adaptation
from utils import nested_update, read_configs, Logger, print_config


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(), override=True)  # take environment variables from .env

parser = argparse.ArgumentParser()
parser.add_argument("--animation", "-a", default=False, action="store_true")
parser.add_argument("config_files", type=str, nargs='+', help="Configuration yaml files.")
parser.add_argument('--episode', '-e', type=int, help="Episode (iteration) number. It is used as part of the log file name.")
parser.add_argument('--seed', '-s', type=int, help="Seed for random number generator.")
parser.add_argument('--extra_config', type=str, help="Extra configuration as JSON string (serialized dict).")
args = parser.parse_args()

# set_verbose(True)
# set_debug(True)

config = read_configs(args.config_files)
if args.extra_config is not None:
    config = nested_update(config, json.loads(args.extra_config))
name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-") + config["name"]
if args.episode is not None:
    name = f"{args.episode:03}-{name}"
log_dir = config["log_dir"]
sys.stdout = Logger(f"{log_dir}/{name}.ansi")
sys.stderr = Logger(f"{log_dir}/{name}.err", sys.stderr, create_on_first_write=True)

if args.seed is not None:
    if config.get("tensorflow_needed", False):
        from keras.utils import set_random_seed
    else:
        from utils import set_random_seed
    set_random_seed(args.seed)

config["log_dir"] = log_dir
config["log_file_name"] = name
config["log_file_path"] = f"{log_dir}/{name}.ansi"
print_config(config)

example = config["example"]
if example == "farm":
    from farm.simulation import SmartFarmSimulation as Simulation
    from farm.visualizer import Visualizer
    from farm.stats import Stats
    from farm.plots import draw_plots
elif example == "dragon":
    from dragon.simulation import DragonHuntSimulation as Simulation
    from dragon.stats import Stats
    from dragon.plots import draw_plots
else:
    raise ValueError(f"Unknown example: {example}")


adaptation = import_adaptation(config)
simulation = Simulation(adaptation.adapt, config)
adaptation.init(simulation)

if args.animation:
    visualizer = Visualizer(simulation)
    simulation.add_visualizer(visualizer)
stats = Stats(simulation, f"{log_dir}/{name}.csv")
simulation.add_stats(stats)
stats.write_header()

print("\nRunning simulation...\n")
simulation.run_simulation(config["steps"])
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
