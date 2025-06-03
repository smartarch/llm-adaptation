import re

from jinja2 import Environment, FileSystemLoader, pass_context

from base_classes.simulation import Simulation
from base_classes.prompt_template import PromptTemplate, ProcessingError


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
def get_ensembles_ctx(context, config: list[str | dict]):
    components = context.get("components")
    ensemble_types = context.get("configuration")["ensembles"]
    environment = context.get("environment")

    yield from get_ensembles(components, config, ensemble_types, environment)


def get_ensembles(components, config, ensemble_types, environment):
    for ensemble in config:
        if isinstance(ensemble, str):  # singleton
            yield ensemble_types[ensemble]
        else:  # instance for each component
            ensemble_type = ensemble_types[ensemble["type"]]
            component_type = eval(ensemble["foreach"], environment.get_globals())
            condition = eval(ensemble.get("if", "True"), environment.get_globals())

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
    jinja_env.filters['get_ensembles'] = get_ensembles_ctx
    return jinja_env


class JinjaPromptTemplate(PromptTemplate):

    def __init__(self, **configuration):
        super().__init__(**configuration)

        jinja_env = prepare_jinja_env()
        self.template = jinja_env.get_template("prompt.jinja")

        self.correct_assignments = {}

    def create_prompt(self, simulation, memory=None):
        return self.template.render(
            components=simulation.components,
            beyond_control_components=simulation.beyond_control_components,
            environment=simulation,
            configuration=self.configuration,
            memory=memory,
            step=simulation.step,
        )

    def process_response(self, response, simulation, is_retry) -> tuple[list[ProcessingError] | None, str | None]:
        if not is_retry:
            self.correct_assignments = {}

        answer = self.extract_tag(response, "answer")
        if not answer:
            error = "Final group assignment not found. You must use the `<answer>` and `</answer>` tags to mark the final answer."
            simulation.append_assignment_error(error)
            return [ProcessingError(None, error)], None
        memory = self.extract_tag(response, "memory")

        components = self.load_components_for_assignments(simulation)

        if is_retry and "retry_format" in self.configuration:
            self.apply_correct_assignments(components, simulation)
            if self.configuration["retry_format"] == "component-first":
                errors = self.process_component_first(answer, components, simulation)
            elif self.configuration["retry_format"] == "ensemble-first":
                errors = self.process_ensemble_first(answer, components, simulation)
            else:
                raise NotImplementedError("Unsupported retry format")
        else:
            if self.configuration["answer_format"] == "component-first":
                errors = self.process_component_first(answer, components, simulation)
            elif self.configuration["answer_format"] == "ensemble-first":
                errors = self.process_ensemble_first(answer, components, simulation)
            else:
                raise NotImplementedError("Unsupported answer format")

        self.clean_up_correct_assignments(errors)
        return errors, memory

    @staticmethod
    def extract_tag(response, tag):
        # This regex looks for content between triple backticks, possibly with a language specifier.
        pattern = rf"<{tag}>(.*?)</{tag}>"
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        return None

    def process_component_first(self, answer, components, simulation):
        rows = answer.split("\n")
        errors: list[ProcessingError] = []
        for row in rows:
            try:
                if row == "" or row == "```":
                    continue
                row = row.replace("- ", "")  # remove leading hyphens
                row = row.replace("**", "")  # remove bold

                tokens = row.split(":")
                if len(tokens) != 2:
                    raise ValueError('Invalid row format, expected "<name>: <group>"')
                component_id, group = tokens
                component_id = component_id.strip()

                if component_id not in components:
                    error = f"Unknown component: {component_id}"
                    errors.append(ProcessingError(row, error))
                    simulation.append_assignment_error(error)
                    continue

                component = components[component_id]
                error = simulation.assign_group(component, group.strip())
                if error:
                    errors.append(ProcessingError(row, error))
                else:
                    self.correct_assignments[component_id] = group.strip()
            except (ValueError, KeyError, IndexError) as error:  # if error is not caught inside assign_group, we don't retry
                print(f"Error - invalid row ({str(error)}): {repr(row)}")
        if len(simulation.assignments) < len(components):
            missing_components = [component_id for component_id, component in components.items() if component not in simulation.assignments]
            error = "The following components have not been assigned to a group: " + ", ".join(missing_components)
            errors.append(ProcessingError(None, error))
            simulation.append_assignment_error(error)
        return errors

    def process_ensemble_first(self, answer, components, simulation):
        rows = answer.split("\n")
        errors: list[ProcessingError] = []
        assigned_groups = set()

        for row in rows:
            try:
                if row == "" or row == "```":
                    continue
                row = row.replace("- ", "")  # remove leading hyphens
                row = row.replace("**", "")  # remove bold

                group, components_list = row.split(":")
                group = group.strip()
                assigned_groups.add(group)
                component_ids = components_list.strip().split(",")

                for component_id in component_ids:
                    component_id = component_id.strip()

                    if component_id == "":
                        continue
                    if component_id not in components:
                        error = f"Unknown component: {component_id}"
                        errors.append(ProcessingError(row, error))
                        simulation.append_assignment_error(error)
                        continue

                    component = components[component_id]
                    error = simulation.assign_group(component, group.strip())
                    if error:
                        errors.append(ProcessingError(row, error))
                    else:
                        self.correct_assignments[component_id] = group.strip()
            except (ValueError, KeyError, IndexError) as error:  # if error is not caught inside assign_group, we don't retry
                print(f"Error - invalid row ({str(error)}): {repr(row)}")
        if len(simulation.assignments) < len(components):
            missing_components = [component_id for component_id, component in components.items() if component not in simulation.assignments]
            error = "The following components have not been assigned to a group: " + ", ".join(missing_components)
            errors.append(ProcessingError(None, error))
            simulation.append_assignment_error(error)

        all_groups = self.load_ensembles_for_assignments(simulation)
        if len(assigned_groups) < len(all_groups):
            missing_groups = [group for group in all_groups if group not in assigned_groups]
            error = "The following groups are missing in the assignment: " + ", ".join(missing_groups)
            errors.append(ProcessingError(None, error))
            simulation.append_assignment_error(error)
        return errors

    def load_components_for_assignments(self, simulation):
        components = {}

        for assignment_config in self.configuration["assignments"].values():
            component_config = assignment_config["components"]
            component_type_config = self.configuration["components"][component_config["type"]]
            id_attr = component_type_config.get("id", "id")

            for component in get_components(component_config, simulation.components, simulation):
                component_id = getattr(component, id_attr)
                components[component_id] = component

        return components

    def load_ensembles_for_assignments(self, simulation):
        ensembles = set()

        for assignment_config in self.configuration["assignments"].values():
            assignment_ensembles = get_ensembles(simulation.components, assignment_config["ensembles"], self.configuration["ensembles"], simulation)
            ensembles.update([ensemble["name"] for ensemble in assignment_ensembles])

        return ensembles

    def clean_up_correct_assignments(self, errors):
        for row, error in errors:
            # TODO: remove incorrectly assigned components from correct_assignments
            pass

    def apply_correct_assignments(self, components, simulation):
        for component_id, group in self.correct_assignments.items():
            component = components[component_id]
            simulation.assign_group(component, group)
