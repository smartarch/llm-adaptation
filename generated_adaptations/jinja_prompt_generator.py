import random
from pathlib import Path

from adaptations.jinja import prepare_jinja_env
from base_classes.adaptation import Adaptation
from base_classes.simulation import Simulation
from utils import print_prompt

PROMPTS_PATH = Path("generated_adaptations/prompts/")


class JinjaPromptGenerator(Adaptation):

    def __init__(self, prompt_template_params, config, **kwargs):
        super().__init__()

        self.configuration = prompt_template_params
        self.name = config["name"].removeprefix("jinja_generator")
        self.example = config["example"]

        jinja_env = prepare_jinja_env()
        # self.template = jinja_env.get_template("generate.jinja")
        self.template = jinja_env.get_template("state_example.jinja")

    def adapt(self, simulation: "Simulation", step: int):
        # move from initial state
        if step == 1:
            self.random_adapt(simulation)
        if step <= 10:
            return

        self.render_prompt(simulation)

    def render_prompt(self, simulation):
        prompt = self.template.render(
            components=simulation.components,
            beyond_control_components=simulation.beyond_control_components,
            environment=simulation,
            configuration=self.configuration,
        )

        print_prompt(prompt)

        (PROMPTS_PATH / f"{self.example}{self.name}.txt").write_text(prompt)

        exit()

    def random_adapt(self, simulation):
        # TODO: this only works for farm -- we can generalize it (move this method to simulation) and use it also in tests
        # assign some drones to fields randomly
        protecting_drones = simulation.drones[:6]
        for drone in protecting_drones:
            drone.assignTarget(random.choice(simulation.fields))
