from adaptations.jinja import prepare_jinja_env
from base_classes.adaptation import Adaptation
from base_classes.simulation import Simulation


class JinjaPromptGenerator(Adaptation):

    def __init__(self, prompt_template_params):
        super().__init__()

        self.configuration = prompt_template_params

        jinja_env = prepare_jinja_env()
        self.template = jinja_env.get_template("generate.jinja")

    def adapt(self, simulation: "Simulation", step: int):
        print(self.template.render(
            components=simulation.components,
            beyond_control_components=simulation.beyond_control_components,
            environment=simulation,
            configuration=self.configuration,
        ))

        exit()
