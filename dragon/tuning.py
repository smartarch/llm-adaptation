"""Grid search over the parameters of the Dragon Hunt with the mock baselines (the results are in dragon/README.md).

For each parameter combination and baseline, it reports:
 * the win rate, the average number of steps to win, and the average remaining HP of the Dragon in the lost games,
   over the runs from the default initial state with seeds 1..SEEDS,
 * the functional constraints (DSL/dragon_constraints.yaml) violated in the test situations (DSL/dragon.yaml),
   with the number of situations in which each constraint was violated.

Usage (from the repository root): python dragon/tuning.py > tuning.md

This script was generated using Claude Code.
"""
import contextlib
import copy
import importlib
import io
import itertools
from collections import Counter

from base_classes.adaptation import import_adaptation
from base_classes.simulation import UserConstraintError
from dragon.simulation import DragonHuntSimulation
from generated_adaptations.generator_utils import simulation_configs, adaptation_config, reset_component_counters
from utils import read_configs, nested_update, set_random_seed

BASELINES = ["greedy_no_meals", "greedy_with_meals", "staggered_meals", "assemble_and_strike"]
SEEDS = 10
STEPS = 30
HP = 100
GRID = {
    "interval": [6, 8],
    "hungry_cannot_attack": [False, True],
    "regeneration": [0, 5, 10],
}


def make_config(baseline: str, params: dict) -> dict:
    config = read_configs(simulation_configs("dragon", True))
    config = copy.deepcopy(nested_update(config, adaptation_config(baseline, "dragon", "mock")))
    config["steps"] = STEPS
    config["dragon"]["HP"] = params.get("hp", HP)
    config["dragon"]["Regeneration"] = params["regeneration"]
    config["meals"]["interval"] = params["interval"]
    config["meals"]["hungry_cannot_attack"] = params["hungry_cannot_attack"]
    return config


def situations(config: dict):
    """Test situations as defined in the DSL (name, seed, arrange function)."""
    for name, situation in config["adaptation_params"]["prompt_template_params"]["situations"].items():
        arrange = None
        if "arrange" in situation:
            module, func = situation["arrange"].rsplit(".", 1)
            arrange = getattr(importlib.import_module(module), func)
        yield name, situation.get("seed", 42), arrange


def run(config: dict, seed: int, arrange=None) -> tuple[bool, int, int, set[str]]:
    """Run one game; returns (won, steps, remaining Dragon HP, violated constraints)."""
    reset_component_counters("dragon")
    set_random_seed(seed)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        adaptation = import_adaptation(config)
        simulation = DragonHuntSimulation(adaptation.adapt, config)
        adaptation.init(simulation)
        if arrange:
            simulation = arrange(simulation)
        errors = []
        simulation.assignment_errors_handler = lambda errs: errors.extend(errs)
        simulation.run_simulation(config["steps"])
        errors += simulation.assignment_errors  # violations at the end of the run
    violated = {e.constraint_name for e in errors if isinstance(e, UserConstraintError)}
    return simulation.dragon.hp <= 0, simulation.step, simulation.dragon.hp, violated


def mean(values: list) -> str:
    return f"{sum(values) / len(values):.1f}" if values else "n/a"


METRICS = {
    "win_rate": "Win rate",
    "steps": "Average number of steps to win",
    "lost_hp": "Average remaining HP of the Dragon in lost games",
    "violations": "Violated constraints (number of test situations in which the constraint was violated)",
}


def evaluate(baseline: str, params: dict) -> dict[str, str]:
    """Returns the formatted values of the METRICS for the baseline with the given parameters."""
    config = make_config(baseline, params)
    games = [run(config, seed) for seed in range(1, SEEDS + 1)]
    wins = [steps for won, steps, _, _ in games if won]
    lost_hp = [hp for won, _, hp, _ in games if not won]
    violations = Counter()
    for _, seed, arrange in situations(config):
        violations.update(run(config, seed, arrange)[3])
    failed = ", ".join(f"`{name}` ({count})" for name, count in sorted(violations.items(), key=lambda x: (-x[1], x[0]))) or "none"
    return {"win_rate": f"{len(wins) / len(games):.0%}", "steps": mean(wins), "lost_hp": mean(lost_hp), "violations": failed}


def print_table(header: list[str], rows: list[list[str]]):
    print("| " + " | ".join(header) + " |")
    print("|" + " --- |" * len(header))
    for row in rows:
        print("| " + " | ".join(row) + " |")
    print()


def main():
    n_situations = len(list(situations(make_config(BASELINES[0], {"interval": 6, "hungry_cannot_attack": True, "regeneration": 5}))))
    print(f"Win rate and steps over {SEEDS} seeds; constraints checked in {n_situations} test situations.\n")
    baseline_columns = [f"`{baseline}`" for baseline in BASELINES]

    # grid search: one table per metric, parameter combinations as rows, baselines as columns
    grid = [dict(zip(GRID, values)) for values in itertools.product(*GRID.values())]
    results = [(params, {baseline: evaluate(baseline, params) for baseline in BASELINES}) for params in grid]
    print(f"### Grid search (Dragon HP = {HP}, {STEPS} steps)\n")
    for metric, title in METRICS.items():
        print(f"#### {title}\n")
        rows = [[str(params["interval"]), "on" if params["hungry_cannot_attack"] else "off", str(params["regeneration"])]
                + [result[b][metric] for b in BASELINES] for params, result in results]
        print_table(["N", "weakness", "R"] + baseline_columns, rows)


if __name__ == "__main__":
    main()
