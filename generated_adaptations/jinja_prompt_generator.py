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
        self.template = jinja_env.get_template("generate.jinja")

    def adapt(self, simulation: "Simulation", step: int):
        prompt = self.template.render(
            components=simulation.components,
            beyond_control_components=simulation.beyond_control_components,
            environment=simulation,
            configuration=self.configuration,
        )

        print_prompt(prompt)

        (PROMPTS_PATH / f"{self.example}{self.name}.txt").write_text(prompt)

        exit()
