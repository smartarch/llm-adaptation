import os
import random
import sys
from datetime import datetime

from langchain.globals import set_verbose, set_debug

from adaptation.openai import create_llm, invoke_template
from llm_templates.groups import GroupsLLMTemplate
from simulation import SmartFarmSimulation
from stats import Stats
from utils import read_yaml, Logger
from visualizer import Visualizer


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(), override=True)  # take environment variables from .env

# set_verbose(True)
# set_debug(True)

config = read_yaml("config.yaml")
name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
sys.stdout = Logger(f"logs/{name}.log")


llm = create_llm()
prompt_template = GroupsLLMTemplate()


def adapt(simulation: SmartFarmSimulation, step: int):
    # if step % 10 == 0:
    #     invoke_template(llm, prompt_template, simulation)

    for drone in simulation.drones:
        if drone.battery < 0.25:
            drone.assignTarget(simulation.charger)
        elif drone.target is None:
            drone.assignTarget(random.choice(simulation.fields))


simulation = SmartFarmSimulation(adapt, config)

visualizer = Visualizer(simulation)
simulation.add_visualizer(visualizer)
visualizer.drawFields()
stats = Stats(simulation, f"logs/{name}.csv")
simulation.add_stats(stats)
stats.write_header()

simulation.run_simulation(200)

print("Saving animation...")
os.makedirs("animations", exist_ok=True)
visualizer.createAnimation(f"logs/{name}.gif")
print("Done")
