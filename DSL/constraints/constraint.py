import dataclasses
from typing import Any, TYPE_CHECKING, Iterator
from DSL.constraints.evaluation import ASTNode, ForAll, TemporalObligation, ForAllViolation
from base_classes.components import Component

if TYPE_CHECKING:
    from base_classes.ensembles import ResolvedEnsemble
    from base_classes.simulation import Simulation


@dataclasses.dataclass
class UserConstraint:
    name: str
    ast: ASTNode
    reason: str  # f-string that will be evaluated later with context
    variables: dict[str, str]
    obligations: list[TemporalObligation] = dataclasses.field(default_factory=list)

    def check(self, simulation: "Simulation", components: list[Component], resolved_ensembles: list["ResolvedEnsemble"]) -> Iterator[str]:
        context = self.prepare_context(simulation, components, resolved_ensembles)
        step: int = simulation.step  # type: ignore
        result = self.ast.evaluate(step, context, {})
        if isinstance(result, list):
            for r in result:
                if isinstance(r, TemporalObligation):
                    if r not in self.obligations:
                        self.obligations.append(r)
                elif isinstance(r, ForAllViolation):
                    yield self.format_reason(r.context)
        if result is False:
            yield self.format_reason(context)

    def check_end(self, simulation: "Simulation", components: list[Component]) -> Iterator[str]:
        context = self.prepare_context(simulation, components, [])
        for obligation in self.obligations:
            if not obligation.resolved and obligation.occurrences < obligation.min_occurrences:
                yield self.format_reason(context | obligation.bound_variables)

    def format_reason(self, context: dict[str, Any]) -> str:
        return eval(f'f"{self.reason}"', context)

    def prepare_context(self, simulation: "Simulation", components: list[Component], resolved_ensembles: list["ResolvedEnsemble"]):
        component_context = self.components_to_eval(simulation, components)
        ensemble_context = self.ensembles_to_eval(simulation, resolved_ensembles)

        context = simulation.get_globals().copy()
        context.update(component_context)
        context.update(ensemble_context)

        for variable_name, expression in self.variables.items():
            context[variable_name] = eval(expression, context)

        context["step"] = simulation.step

        return context

    def components_to_eval(self, simulation: "Simulation", components: list["Component"]):
        context = {}
        for component_type in simulation.dsl_config.data["components"]:
            name = component_type + "Comps"
            context[name] = [
                c for c in components
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
            else:  # singleton
                name = ensemble_type + "En"
                context[name] = next((
                    e for e in resolved_ensembles
                    if e.type == ensemble_type
                ), None)
        return context
