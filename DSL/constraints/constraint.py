"""
ConstraintMonitor scaffolding for temporal logic DSL.
"""

import dataclasses
from typing import Callable, TYPE_CHECKING
from DSL.constraints.parser import ASTNode
from base_classes.components import Component

if TYPE_CHECKING:
    from base_classes.ensembles import ResolvedEnsemble
    from base_classes.simulation import Simulation


@dataclasses.dataclass
class UserConstraint:
    name: str
    ast: ASTNode
    reason: Callable

    def check(self, simulation: "Simulation", components, resolved_ensembles):
        component_locals = self.components_to_eval(simulation, components)
        ensemble_locals = self.ensembles_to_eval(simulation, resolved_ensembles)
        # TODO: evaluate the AST using eval and the locals

    def components_to_eval(self, simulation: "Simulation", components: dict[str, "Component"]):
        variables = {}
        for component_type in simulation.dsl_config.data["components"]:
            name = component_type + "Comps"
            variables[name] = [
                c for c in components.values()
                if isinstance(c, eval(component_type, simulation.get_globals()))
            ]
        return variables
    
    def ensembles_to_eval(self, simulation: "Simulation", resolved_ensembles: list["ResolvedEnsemble"]):
        variables = {}
        for ensemble_type, ensemble_config in simulation.dsl_config.data["ensembles"].items():
            if "params" in ensemble_config:
                name = ensemble_type + "Ens"
                variables[name] = {
                    e.param: e
                    for e in resolved_ensembles
                    if e.type == ensemble_type
                }
            else: # singleton
                name = ensemble_type + "En"
                variables[name] = next((
                    e for e in resolved_ensembles
                    if e.type == ensemble_type
                ), None)
        return variables



class ConstraintViolation:
    constraint: UserConstraint

    # occurrences: int = 0
    # violations: int = 0
    # reason: str
    # step: int
