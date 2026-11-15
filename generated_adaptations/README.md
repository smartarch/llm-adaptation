# Vibe coding with feedback

The [`generator.py`](./generator.py) script implements the vibe coding with feedback loop for generating adaptation managers (AMs) for the two use cases (Dragon Hunt and Smart Farm). Use the help of the script to see the available options:

```bash
python generated_adaptations/generator.py --help
```

See the [experiment notebooks](../experiments) for experiments using the vibe coding tool. The experiments can be run in parallel with [`experiments/parallel_runs.py`](../experiments/parallel_runs.py), which limits the number of runs at the same time, both globally and per LLM.

The [`generator.py`](./generator.py) also performs the constraint verification (see below) and runs a simulation of the use case with the generated AM to collect metrics.

## Feedback modes

The `--mode` option selects the feedback given to the LLM after each iteration:

| Mode | Feedback | Template |
| --- | --- | --- |
| `stats` | simulation statistics averaged over the runs | `prompts/{example}_stats.md` |
| `progress` | simulation metrics step by step for each run (Dragon Hunt only) | `prompts/dragon_progress.md` |
| `system` | report of the system constraints (unit tests) | `prompts/test.md` |
| `required` | report of the system + required functional constraints | `prompts/test.md` |
| `all` | report of the system + required + optional functional constraints | `prompts/test.md` |
| `result` | only the simulation result (win rate / damage); currently not used in the experiments | `prompts/{example}_result.md` |

When the tests of the mode pass, but the simulation result is not good enough, `prompts/{example}_testpass.md` is used instead.

The AM is **valid** if it satisfies the system and the required functional constraints; the optional constraints only give feedback. The loop stops when the AM is valid and the simulation result is good enough (`verdict`).

In every iteration, the system, required and optional constraints are also checked separately (`results/code_XX_test_{system,functional,optional}_{pass,fail}.txt`) for the analysis. In modes `required` and `all`, the report of that level is saved as well (`results/code_XX_test_{required,all}_*.txt`).

## Prompt generation

The prompts are prepared in [`prompts_user`](./prompts_user). They can be generated from the DSL architecture specification files (run this from the repository root directory):

```bash
python main.py dragon/configs/default.yaml generated_adaptations/jinja_prompt_generator.yaml DSL/dragon.yaml dragon/configs/strategy.yaml -e 1 -s 1
```

And similarly for the farm use case. The "functional requirements" (`*_requirements` variant of the prompt) are not yet generated automatically, but they can be added manually by copy-pasting the `reason` message for each constraint.

## Constraint verification via unit tests

The constraint verification is implemented as unit tests in [`pytest`](https://docs.pytest.org/en/stable/) in the [`generated_adaptations/tests`](./tests) folder. The generic ("system") constraints are separated into several unit tests, while the functional ("user") constraints are grouped into one test for the required and one for the optional constraints (the tests load the constraints from the architecture specification DSL files and uses the [FCL monitor](../fcl/README.md) for constraint evaluation, see also [`DSL/constraints`](../DSL/constraints/README.md)). The files specific to each use case contain functions for setting up the initial state of the system (simulation) for testing.

### Running the tests from command line

To run the tests from the terminal, use `pytest generated_adaptations/tests` from the project root directory (`llm-adaptation`).
It might be necessary to add the root directory to the Python path for the imports to work:
Windows: `set PYTHONPATH=%PYTHONPATH%;.`,
Linux: `PYTHONPATH=$PYTHONPATH:.`

The `--example`, `--variant`, `--adaptation_name` and `--tests` options select the AM and the tests. `--tests` selects the level:

* `system`: only the system constraints;
* `functional`: only the required functional constraints;
* `optional`: only the optional functional constraints;
* `required`: system + required functional constraints (validity of the AM);
* `all`: system + required + optional functional constraints.

For example:

```bash
pytest generated_adaptations/tests -q --tb=short -rfExX --show-capture=no --color=no -p no:cacheprovider --example=dragon --adaptation_name=staggered_meals --variant=mock --tests=required
```

### `pytest` options

We use custom formatting of the output of `pytest` as the output is directly used as feedback to the LLM in the vibe coding loop. The [`conftest.py`](./tests/conftest.py) file contains customizations for the test runner and reporting, and the following options are used: `-q` (less verbose output, we could also use `--no-header` instead to remove only platform, rootdir, plugins info), `--tb=no` (remove tracebacks, we could possibly also use `--tb=short` or `--tb=line` as information is in the summary are trimmed if the terminal is not wide enough), `--show-capture=no` (hide simulation `stdout` and `stderr` in the output).
