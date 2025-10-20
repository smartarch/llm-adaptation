import dataclasses
from collections import UserDict
from typing import Iterator, Callable

from DSL.constraints.constraint import UserConstraint
from DSL.constraints.parser import parse_constraint
from base_classes.components import Component


class DSLConfiguration(UserDict):

    def load_assignment_names(self) -> list[str]:
        return self.data["assignments"].keys()

    def load_assignment_configs(self) -> list[tuple[str, dict]]:
        return self.data["assignments"].items()

    def load_components_for_all_assignments(self, simulation) -> dict[str, Component]:
        components = {}
        for assignment_name in self.data["assignments"]:
            components.update(self.load_components_for_assignment(simulation, assignment_name))
        return components

    def load_components_for_assignment(self, simulation, assignment_name) -> dict[str, Component]:
        assignment_config = self.data["assignments"][assignment_name]
        components_config = assignment_config["components"]
        components_type_config = self.data["components"][components_config["type"]]
        id_attr = components_type_config.get("id", "id")

        return {
            getattr(component, id_attr): component
            for component in get_components_for_assignment(components_config, simulation.components, simulation)
        }

    def load_ensemble_instances_for_all_assignments(self, simulation) -> list["EnsembleInstance"]:
        ensembles = []
        for assignment_name in self.data["assignments"]:
            ensemble_instances = self.load_ensemble_instances_for_assignment(simulation, assignment_name)
            ensembles.extend(ensemble_instances)
        return ensembles
    
    def load_ensemble_names_for_all_assignments(self, simulation) -> list[str]:
        return [ensemble.name for ensemble in self.load_ensemble_instances_for_all_assignments(simulation)]

    def load_ensemble_instances_for_assignment(self, simulation, assignment_name) -> list["EnsembleInstance"]:
        assignment_config = self.data["assignments"][assignment_name]
        ensembles_config = assignment_config["ensembles"]
        ensemble_types = self.data["ensembles"]

        return list(get_ensemble_instances_for_assignment(ensembles_config, ensemble_types, simulation.components + simulation.beyond_control_components, simulation))

    def load_constraints(self, simulation, assignment_name) -> Iterator["UserConstraint"]:
        if assignment_name is not None:
            config = self.data.get("assignments", {}).get(assignment_name, {}).get("constraints", {})
        else:
            config = self.data.get("constraints", {})

        for constraint_name, constraint in config.items():
            ast = parse_constraint(constraint["constraint"])
            print(ast)  # TODO: remove after debugging
            yield UserConstraint(
                name=constraint_name,
                ast=ast,
                reason=constraint["reason"],
                variables=constraint.get("variables", {})
            )

    def load_constraints_for_all_assignments(self, simulation) -> Iterator["UserConstraint"]:
        for assignment_name in self.data.get("assignments", {}):
            yield from self.load_constraints(simulation, assignment_name)
        yield from self.load_constraints(simulation, None)


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


def get_ensemble_instances_for_assignment(ensembles_config, ensemble_types, components, environment):
    for ensemble_config in ensembles_config:
        if isinstance(ensemble_config, str):  # singleton
            yield EnsembleInstance(type=ensemble_config, **ensemble_types[ensemble_config])
        else:  # instance for each component
            ensemble_type = ensemble_types[ensemble_config["type"]]
            component_type = eval(ensemble_config["foreach"], environment.get_globals())
            condition = eval(ensemble_config.get("if", "lambda _: True"), environment.get_globals())  # TODO: the condition only work for one parameter

            filtered_components = filter(lambda c: isinstance(c, component_type), components)
            filtered_components = filter(condition, filtered_components)

            name_generator = eval(ensemble_type["name"])

            for component in filtered_components:
                ensemble = EnsembleInstance(type=ensemble_config["type"], name=name_generator(component))
                if "description" in ensemble_type:
                    ensemble.description = ensemble_type["description"]
                # if the ensemble has parameters, the component is the first parameter
                if "params" in ensemble_type:
                    first_param = next(iter(ensemble_type["params"]))  # TODO: how to handle multiple parameters?
                    setattr(ensemble, first_param, component)
                    ensemble.param = component
                yield ensemble


@dataclasses.dataclass
class EnsembleInstance:
    type: str
    name: str
    description: str | None = None
    param: Component | None = None


@dataclasses.dataclass
class Situation:
    name: str
    seed = 42
    steps = None
    config: dict

    def __str__(self):
        return self.name
