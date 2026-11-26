"""Evaluation of generated Dragon Hunt AMs in more situations (seeds and initial conditions) than in the vibe-coding loop.

Each game is run in-process (as in dragon/tuning.py) with all the functional constraints (required and optional) enabled,
so that one run gives both the result of the game and all the violated constraints. The games run in parallel processes.

Usage (from the repository root, e.g. in experiments/dragon.ipynb):
    situations = situation_grid(seeds=range(1, 6), warriors=[True, False], wheat=range(10, 16))
    results = evaluate(code_files, situations)

This script was generated using Claude Code.
"""
import contextlib
import io
import itertools
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from base_classes.adaptation import import_adaptation
from base_classes.simulation import AssignmentError, UserConstraintError
from generated_adaptations.generator_utils import simulation_configs, optional_constraint_names, reset_component_counters
from utils import read_configs, nested_update, set_random_seed


@dataclass(frozen=True)
class Situation:
    seed: int
    warriors: bool = True  # False = the initial warriors are removed (as in the "no_initial_warriors" test situation)
    wheat: int = 10  # initial wheat (10 in dragon/configs/default.yaml)

    def __str__(self):
        return f"seed={self.seed},warriors={'yes' if self.warriors else 'no'},wheat={self.wheat}"


def situation_grid(seeds, warriors=(True,), wheat=(10,)) -> list[Situation]:
    """All combinations of the given seeds, initial warriors (yes / no) and initial wheat."""
    return [Situation(s, w, h) for s, w, h in itertools.product(seeds, warriors, wheat)]


def am_name(code_file: Path) -> str:
    """Name of the AM, e.g. "all_new/gpt6luna_01/code_16" (the last three parts of the path)."""
    return "/".join(Path(code_file).with_suffix("").parts[-3:])


def am_config(code_file: Path) -> dict:
    """Config of the Dragon Hunt with the AM from `code_file` (a path relative to the repository root) and all the constraints."""
    config = read_configs(simulation_configs("dragon", required=True, optional="all"))
    module = ".".join(Path(code_file).with_suffix("").parts)
    return nested_update(config, {"name": am_name(code_file), "adaptation_name": f"{module}.SmartAdaptation"})


def run_game(code_file: Path, situation: Situation) -> dict:
    """Run one game; returns the result of the game and the violated constraints (constraint name -> True)."""
    config = am_config(code_file)
    reset_component_counters("dragon")
    set_random_seed(situation.seed)
    errors: list[AssignmentError] = []
    exceptions: list[str] = []
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from dragon.simulation import DragonHuntSimulation
        from generated_adaptations.tests.dragon import remove_warriors, set_initial_wheat
        adaptation = import_adaptation(config)
        simulation = DragonHuntSimulation(adaptation.adapt, config)
        adaptation.init(simulation)
        if not situation.warriors:
            simulation = remove_warriors(simulation)
        simulation = set_initial_wheat(simulation, situation.wheat)
        simulation.assignment_errors_handler = lambda errs: errors.extend(errs)
        simulation.adapt_exception_handler = lambda e: exceptions.append(f"{type(e).__name__}: {e}")
        simulation.run_simulation(config["steps"])
        errors += simulation.assignment_errors  # violations at the end of the run

    won = simulation.dragon.hp <= 0
    result = {"am": am_name(code_file), "seed": situation.seed, "warriors": situation.warriors, "wheat": situation.wheat,
              "won": won, "steps": simulation.step if won else None, "dragon_hp": max(0, simulation.dragon.hp),
              "exceptions": len(exceptions)}
    for error in errors:
        if isinstance(error, UserConstraintError):
            result[error.constraint_name] = True
        else:
            result[f"system: {type(error).__name__}"] = True
    return result


def _run_game(args):
    return run_game(*args)


def evaluate(code_files: list[Path], situations: list[Situation], processes: int | None = None) -> pd.DataFrame:
    """Runs every AM in every situation (in parallel processes); one row per game, one bool column per violated constraint.

    The column "valid" = no system errors, no exceptions in the AM and no violated required constraints (incl. game_is_won).
    The column "optional_ok" = no violated optional constraints.
    """
    tasks = [(Path(code_file), situation) for code_file in code_files for situation in situations]
    with ProcessPoolExecutor(max_workers=processes or os.cpu_count()) as executor:
        rows = list(executor.map(_run_game, tasks, chunksize=max(1, len(tasks) // (8 * (processes or os.cpu_count())))))
        # read in a worker (like the constraints of the games), so that a stale module in a notebook kernel does not matter
        optional = executor.submit(optional_constraint_names, "dragon").result()
    results = pd.DataFrame(rows)
    violation_columns = [col for col in results.columns if col not in Situation.__dataclass_fields__ and col not in {"am", "won", "steps", "dragon_hp", "exceptions"}]
    results[violation_columns] = results[violation_columns].eq(True)  # NaN = not violated
    required_or_system = [col for col in violation_columns if col not in optional]
    results["valid"] = ~results[required_or_system].any(axis=1) & (results["exceptions"] == 0)
    results["optional_ok"] = ~results[[col for col in violation_columns if col in optional]].any(axis=1)
    return results
