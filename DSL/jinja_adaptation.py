from jinja2 import Environment, FileSystemLoader, pass_context

from base_classes.adaptation import Adaptation
from base_classes.simulation import Simulation
from utils import read_yaml


@pass_context
def get_components(context, config):
    components = context.get("components")
    environment: Simulation = context.get("environment")

    if "type" in config:
        components = filter(lambda c: type(c).__name__ in config["type"], components)
    if "if" in config:
        condition = eval(config["if"], environment.get_globals())
        components = filter(condition, components)
    return list(components)


@pass_context
def get_value(context, component, attribute):
    # environment = context.get("environment")
    # value = eval(getter, {"component": component, "environment": environment})
    # if callable(value):
    #     return value(component)
    value = getattr(component, attribute)
    return value


@pass_context
def get_attr(context, component, config):
    getter = config["attribute"]
    format = config.get("format", "{}")
    value = get_value(context, component, getter)
    if format.startswith('lambda'):
        format = eval(format)
        return format(value)
    if format.startswith('f"') or format.startswith("f'"):
        return eval(format, {"value": value})
    return format.format(value)


@pass_context
def get_ensembles(context, config):
    components = context.get("components")

    for name, ensemble in config.items():
        if isinstance(ensemble, str):
            yield ensemble
        if isinstance(ensemble, dict):
            yield f"{ensemble['name']}: {ensemble['description']}"
        if "for" in ensemble:
            components = filter(lambda c: type(c).__name__ == ensemble["for"], components)
            for component in components:
                yield eval(ensemble["name"], {"component": component})


class JinjaPromptGenerator(Adaptation):

    def __init__(self):
        loader = FileSystemLoader("DSL/templates")
        jinja_env = Environment(
            loader=loader,
            autoescape=False,
            trim_blocks=True,
        )
        jinja_env.filters['get_components'] = get_components
        jinja_env.filters['get_value'] = get_value
        jinja_env.filters['get_attr'] = get_attr
        jinja_env.filters['get_ensembles'] = get_ensembles
        self.template = jinja_env.get_template("prompt.jinja")
        # self.template = jinja_env.get_template("generate.jinja")
        # self.configuration = read_yaml("DSL/drones.yaml")
        self.configuration = read_yaml("DSL/dragon.yaml")

    def adapt(self, simulation: "Simulation", step: int):
        # components = list(simulation.availableDrones())
        components = simulation.components

        print(self.template.render(
            components=components,
            environment=simulation,
            configuration=self.configuration,
        ))

        exit()
