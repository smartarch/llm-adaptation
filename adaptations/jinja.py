from jinja2 import Environment, FileSystemLoader, pass_context

from base_classes.simulation import Simulation
from base_classes.prompt_template import PromptTemplate


@pass_context
def get_components_ctx(context, config, beyond_control=False):
    components = context.get("components")
    if beyond_control:
        components = components + context.get("beyond_control_components")
    environment: Simulation = context.get("environment")
    return get_components(config, components, environment)


def get_components(config, components, environment):
    if "type" in config:
        component_type = eval(config["type"], environment.get_globals())
        components = filter(lambda c: isinstance(c, component_type), components)
    if "if" in config:
        condition = eval(config["if"], environment.get_globals())
        components = filter(condition, components)
    return list(components)


@pass_context
def show_attr(context, component, config):
    if "if" not in config:
        return True

    environment: Simulation = context.get("environment")
    condition = eval(config["if"], environment.get_globals())
    return condition(component)


def get_attr(component, attribute, config):
    format = config.get("format", "{}")
    value = getattr(component, attribute)
    if format.startswith('lambda'):
        format = eval(format)
        return format(value)
    if format.startswith('f"') or format.startswith("f'"):
        return eval(format, {"value": value})
    return format.format(value)


@pass_context
def get_ensembles(context, config: list[str | dict]):
    components = context.get("components")
    ensemble_types = context.get("configuration")["ensembles"]

    for ensemble in config:
        if isinstance(ensemble, str):  # singleton
            yield ensemble_types[ensemble]
        else:  # instance for each component
            ensemble_type = ensemble_types[ensemble["type"]]
            component_type = eval(ensemble["foreach"], context.get("environment").get_globals())
            condition = eval(ensemble.get("if", "True"), context.get("environment").get_globals())

            components = filter(lambda c: isinstance(c, component_type), components)
            components = filter(condition, components)

            name_generator = eval(ensemble_type["name"])

            for component in components:
                yield {
                    **ensemble_type,
                    "name": name_generator(component),
                }


def prepare_jinja_env():
    loader = FileSystemLoader("DSL/templates")
    jinja_env = Environment(
        loader=loader,
        autoescape=False,
        trim_blocks=True,
    )
    jinja_env.filters['get_components'] = get_components_ctx
    jinja_env.filters['show_attr'] = show_attr
    jinja_env.filters['get_attr'] = get_attr
    jinja_env.filters['get_ensembles'] = get_ensembles
    return jinja_env


class JinjaPromptTemplate(PromptTemplate):

    def __init__(self, **configuration):
        super().__init__()
        self.configuration = configuration

        jinja_env = prepare_jinja_env()
        self.template = jinja_env.get_template("prompt.jinja")

    def create_prompt(self, simulation):
        return self.template.render(
            components=simulation.components,
            beyond_control_components=simulation.beyond_control_components,
            environment=simulation,
            configuration=self.configuration,
        )

    def process_response(self, response, simulation):
        parts = response.split("---")
        assignment = parts[-1] if len(parts) > 0 else ""
        rows = assignment.split("\n")

        components = self.load_components_for_assignments(simulation)

        # TODO: this is only component-first, add also ensemble-first
        for row in rows:
            try:
                if row == "" or row == "```":
                    continue
                row = row.replace("- ", "")  # remove leading hyphens
                row = row.replace("**", "")  # remove bold

                component_id, group = row.split(":")
                component = components[component_id.strip()]
                simulation.assign_group(component, group.strip())
            except (ValueError, KeyError, IndexError) as error:
                print(f"Invalid row ({repr(error)}): {repr(row)}")

    def load_components_for_assignments(self, simulation):
        components = {}

        for assignment_config in self.configuration["assignments"].values():
            component_config = assignment_config["components"]
            id_attr = component_config.get("id", "id")

            for component in get_components(component_config, simulation.components, simulation):
                component_id = getattr(component, id_attr)
                components[component_id] = component

        return components
