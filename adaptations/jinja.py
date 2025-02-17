from jinja2 import Environment, FileSystemLoader, pass_context

from base_classes.simulation import Simulation
from base_classes.prompt_template import PromptTemplate


@pass_context
def get_components(context, config, beyond_control=False):
    components = context.get("components")
    if beyond_control:
        components += context.get("beyond_control_components")
    environment: Simulation = context.get("environment")

    if "type" in config:
        components = filter(lambda c: type(c).__name__ in config["type"], components)
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
def get_ensembles(context, config: dict[str, str | dict]):
    components = context.get("components")

    for name, ensemble in config.items():
        if isinstance(ensemble, str):
            yield {"name": ensemble}
        elif "for" in ensemble:
            components = filter(lambda c: type(c).__name__ == ensemble["for"], components)
            name_generator = eval(ensemble["name"])
            for component in components:
                yield {
                    **ensemble,
                    "name": name_generator(component),
                }
        else:
            yield ensemble


def prepare_jinja_env():
    loader = FileSystemLoader("DSL/templates")
    jinja_env = Environment(
        loader=loader,
        autoescape=False,
        trim_blocks=True,
    )
    jinja_env.filters['get_components'] = get_components
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

        exit()

        answer = self.extract_answer(response)
        drone_rows = answer.split("\n")

        assigned_drones = []

        for row in drone_rows:
            try:
                if row == "" or row == "```":
                    continue
                row = row.replace("- ", "")  # remove leading hyphens
                row = row.replace("**", "")  # remove bold

                drone_id, group = row.split(":")
                drone = simulation.dronesDict[drone_id.strip()]
                assigned_drones.append(drone)
                if group.strip() == "idle":
                    drone.assignTarget(None)
                elif group.strip() == "charging":
                    drone.assignTarget(simulation.charger)
                elif group.strip().startswith("protecting"):
                    field_id = group.strip().split()[1]
                    field_idx = int(field_id[-1]) - 1
                    drone.assignTarget(simulation.fields[field_idx])
                else:
                    print(f"Unknown group: {group}")
            except (ValueError, KeyError, IndexError) as error:
                print(f"Invalid row ({error}): {repr(row)}")

        total_assignments = len(assigned_drones)
        unique_drones = set(assigned_drones)
        if len(unique_drones) != total_assignments or total_assignments != len(self.available_drones(simulation)):
            print(
                f"Wrong groups assignment. Unique drones: {len(unique_drones)}, total_assignments: {total_assignments}, available_drones: {len(self.available_drones(simulation))}")
