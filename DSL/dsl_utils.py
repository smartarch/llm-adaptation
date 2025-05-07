from collections import UserDict


class DSLConfiguration(UserDict):

    def load_components_for_assignments(self, simulation):
        components = {}

        for assignment_config in self.data["assignments"].values():
            components_config = assignment_config["components"]
            components_type_config = self.data["components"][components_config["type"]]
            id_attr = components_type_config.get("id", "id")

            for component in get_components_for_assignment(components_config, simulation.components, simulation):
                component_id = getattr(component, id_attr)
                components[component_id] = component

        return components

    def load_ensembles_for_assignments(self, simulation):
        ensembles = set()

        for assignment_config in self.data["assignments"].values():
            assignment_ensembles = get_ensembles_for_assignment(assignment_config["ensembles"], self.data["ensembles"], simulation.components, simulation)
            ensembles.update([ensemble["name"] for ensemble in assignment_ensembles])

        return ensembles


def get_components_for_assignment(components_config, components, environment):
    if "type" in components_config:
        component_type = eval(components_config["type"], environment.get_globals())
        components = filter(lambda c: isinstance(c, component_type), components)
    if "if" in components_config:
        condition = eval(components_config["if"], environment.get_globals())
        components = filter(condition, components)
    return list(components)


def get_attr(component, attribute, config):
    formatter = config.get("format", "{}")
    value = getattr(component, attribute)
    if formatter.startswith('lambda'):
        formatter = eval(formatter)
        return formatter(value)
    if formatter.startswith('f"') or formatter.startswith("f'"):
        return eval(formatter, {"value": value})
    return formatter.format(value)


def get_ensembles_for_assignment(ensembles_config, ensemble_types, components, environment):
    for ensemble in ensembles_config:
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
