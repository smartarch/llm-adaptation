import os
import random

from langchain.globals import set_verbose, set_debug

from adaptation.openai import create_llm, invoke_template
from llm_templates.groups import GroupsLLMTemplate
from simulation import SmartFarmSimulation
from utils import read_yaml
from visualizer import Visualizer


from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(), override=True)  # take environment variables from .env.

# set_verbose(True)
# set_debug(True)


llm = create_llm()
prompt_template = GroupsLLMTemplate()


def adapt(simulation: SmartFarmSimulation, step: int):
    if step % 10 == 0:
        invoke_template(llm, prompt_template, simulation)

    # for drone in simulation.drones:
    #     if drone.battery < 0.2:
    #         drone.assignTarget(simulation.charger)
    #     elif drone.target is None:
    #         drone.assignTarget(random.choice(simulation.fields))


config = read_yaml("config.yaml")

simulation = SmartFarmSimulation(adapt, config)

visualizer = Visualizer(simulation)
simulation.add_visualizer(visualizer)
visualizer.drawFields()

simulation.run_simulation(200)

print("Saving animation...")
os.makedirs("animations", exist_ok=True)
visualizer.createAnimation(f"animations/output.gif")
print("Done")
