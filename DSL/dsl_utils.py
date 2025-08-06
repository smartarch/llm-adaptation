import dataclasses
from collections import UserDict
from typing import Iterator

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

    def load_ensemble_names_for_all_assignments(self, simulation) -> list[str]:
        ensembles = []
        for assignment_name in self.data["assignments"]:
            ensemble_instances = self.load_ensemble_instances_for_assignment(simulation, assignment_name)
            ensembles.extend([ensemble.name for ensemble in ensemble_instances])
        return ensembles

    def load_ensemble_instances_for_assignment(self, simulation, assignment_name) -> list["EnsembleInstance"]:
        assignment_config = self.data["assignments"][assignment_name]
        ensembles_config = assignment_config["ensembles"]
        ensemble_types = self.data["ensembles"]

        return list(get_ensemble_instances_for_assignment(ensembles_config, ensemble_types, simulation.components, simulation))

    def load_constraints(self, simulation, assignment_name, resolved_ensembles, components) -> Iterator["UserConstraint"]:
        if assignment_name is not None:
            config = self.data.get("assignments", {}).get(assignment_name, {}).get("constraints", [])
        else:
            config = self.data.get("constraints", [])

        eval_globals = simulation.get_globals() | {
            "components": components,
            "ensembles": resolved_ensembles,
        }

        for constraint in config:
            relevant_ensembles = resolved_ensembles
            if "foreach" in constraint:
                relevant_ensembles = list(filter(lambda e: e.type == constraint["foreach"], relevant_ensembles))
            if "if" in constraint:
                condition = eval(constraint["if"], eval_globals)
                relevant_ensembles = list(filter(condition, relevant_ensembles))
            yield UserConstraint(
                constraint=eval(constraint["constraint"], eval_globals),
                relevant_ensembles=relevant_ensembles,
                reason=eval(constraint["reason"], eval_globals),
                foreach="foreach" in constraint,
            )


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
            condition = eval(ensemble_config.get("if", "True"), environment.get_globals())  # TODO: the condition only work for one parameter

            components = filter(lambda c: isinstance(c, component_type), components)
            components = filter(condition, components)

            name_generator = eval(ensemble_type["name"])

            for component in components:
                ensemble = EnsembleInstance(type=ensemble_config["type"], name=name_generator(component))
                if "description" in ensemble_type:
                    ensemble.description = ensemble_type["description"]
                # if the ensemble has parameters, the component is the first parameter
                if "params" in ensemble_type:
                    first_param = next(iter(ensemble_type["params"]))  # TODO: how to handle multiple parameters?
                    setattr(ensemble, first_param, component)
                yield ensemble


@dataclasses.dataclass
class EnsembleInstance:
    type: str
    name: str
    description: str | None = None


@dataclasses.dataclass
class UserConstraint:
    constraint: callable
    relevant_ensembles: list[EnsembleInstance]
    reason: callable
    foreach: bool = False
