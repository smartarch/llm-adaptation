import dataclasses
from typing import Callable, TYPE_CHECKING
from DSL.constraints.evaluation import ASTNode, TemporalObligation
from base_classes.components import Component

if TYPE_CHECKING:
    from base_classes.ensembles import ResolvedEnsemble
    from base_classes.simulation import Simulation


@dataclasses.dataclass
class UserConstraint:
    name: str
    ast: ASTNode
    reason: Callable
    variables: dict[str, str]
    obligations: list[TemporalObligation] = dataclasses.field(default_factory=list)

    def check(self, simulation: "Simulation", components, resolved_ensembles):
        context = self.prepare_context(simulation, components, resolved_ensembles)
        step: int = simulation.step  # type: ignore
        result = self.ast.evaluate(step, context, {})
        if isinstance(result, list):
            for obligation in result:
                if obligation not in self.obligations:
                    self.obligations.append(obligation)
        else:
            if result is False:
                print(f"CONSTRAINT VIOLATED: {self.name} at step {step}")  # TODO: proper reason

    def prepare_context(self, simulation: "Simulation", components, resolved_ensembles):
        component_context = self.components_to_eval(simulation, components)
        ensemble_context = self.ensembles_to_eval(simulation, resolved_ensembles)

        context = simulation.get_globals().copy()
        context.update(component_context)
        context.update(ensemble_context)

        for variable_name, expression in self.variables.items():
            context[variable_name] = eval(expression, context)

        return context

    def components_to_eval(self, simulation: "Simulation", components: dict[str, "Component"]):
        context = {}
        for component_type in simulation.dsl_config.data["components"]:
            name = component_type + "Comps"
            context[name] = [
                c for c in components.values()
                if isinstance(c, eval(component_type, simulation.get_globals()))
            ]
        return context
    
    def ensembles_to_eval(self, simulation: "Simulation", resolved_ensembles: list["ResolvedEnsemble"]):
        context: dict[str, dict["Component", "ResolvedEnsemble"] | "ResolvedEnsemble" | None] = {}
        for ensemble_type, ensemble_config in simulation.dsl_config.data["ensembles"].items():
            if "params" in ensemble_config:
                name = ensemble_type + "Ens"
                context[name] = {
                    e.param: e
                    for e in resolved_ensembles
                    if e.type == ensemble_type
                    and e.param is not None  # this should always hold if "params" is in config
                }
            else: # singleton
                name = ensemble_type + "En"
                context[name] = next((
                    e for e in resolved_ensembles
                    if e.type == ensemble_type
                ), None)
        return context



class ConstraintViolation:
    constraint: UserConstraint

    # occurrences: int = 0
    # violations: int = 0
    # reason: str
    # step: int
