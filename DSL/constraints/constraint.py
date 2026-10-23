import dataclasses
from typing import Any, TYPE_CHECKING, Iterator

from fcl import Formula, Monitor, Violation
from base_classes.components import Component

if TYPE_CHECKING:
    from base_classes.ensembles import ResolvedEnsemble
    from base_classes.simulation import Simulation


@dataclasses.dataclass
class UserConstraint:
    """Functional constraint defined in the DSL, monitored by an FCL monitor during a simulation run."""
    name: str
    formula: Formula
    reason: str  # f-string that will be evaluated later with context
    variables: dict[str, str]
    monitor: Monitor | None = dataclasses.field(init=False, default=None)

    def start(self, simulation: "Simulation", trace_length: int, components: list[Component], resolved_ensembles: list["ResolvedEnsemble"]) -> Iterator[tuple[int, str]]:
        """Start monitoring a new run (with the initial state of the system); yields (step, reason) of violations."""
        self.monitor = Monitor(self.formula, trace_length)
        context = self.prepare_context(simulation, components, resolved_ensembles)
        for violation in self.monitor.start(context):
            yield violation.step, self.format_reason(violation)

    def check(self, simulation: "Simulation", components: list[Component], resolved_ensembles: list["ResolvedEnsemble"]) -> Iterator[tuple[int, str]]:
        """Check the current step; yields (step, reason) of violations."""
        assert self.monitor is not None, "UserConstraint.start must be called first"
        context = self.prepare_context(simulation, components, resolved_ensembles)
        existing_objects = simulation.components + simulation.beyond_control_components
        for violation in self.monitor.step(context, existing_objects=existing_objects):
            yield violation.step, self.format_reason(violation)

    def check_end(self) -> Iterator[tuple[int, str]]:
        """Finish the run; yields (step, reason) of violations."""
        if self.monitor is None:
            return
        for violation in self.monitor.finish():
            yield violation.step, self.format_reason(violation)

    def format_reason(self, violation: Violation) -> str:
        context = dict(violation.state) | dict(violation.bindings) | {
            "step": violation.step,
            "trigger_step": violation.trigger_step,
            "trigger_state": violation.trigger_state,
        }
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
