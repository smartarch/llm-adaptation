# Vibe coding with feedback

The [`generator.py`](./generator.py) script implements the vibe coding with feedback loop for generating adaptation managers (AMs) for the two use cases (Dragon Hunt and Smart Farm). Use the help of the script to see the available options:

```bash
python generated_adaptations/generator.py --help
```

See the [experiment notebooks](../experiments) for experiments using the vibe coding tool.

The [`generator.py`](./generator.py) also performs the constraint verification (see below) and runs a simulation of the use case with the generated AM to collect metrics.

## Prompt generation

The prompts are prepared in [`prompts_user`](./prompts_user). They can be generated from the DSL architecture specification files (run this from the repository root directory):

```bash
python main.py dragon/configs/default.yaml generated_adaptations/jinja_prompt_generator.yaml DSL/dragon.yaml dragon/configs/strategy.yaml -e 1 -s 1
```

And similarly for the farm use case. The "functional requirements" (`*_requirements` variant of the prompt) are not yet generated automatically, but they can be added manually by copy-pasting the `reason` message for each constraint.

## Constraint verification via unit tests

The constraint verification is implemented as unit tests in [`pytest`](https://docs.pytest.org/en/stable/) in the [`generated_adaptations/tests`](./tests) folder. The generic ("system") constraints are separated into several unit tests, while the functional ("user") constraints are grouped into a single unit test (the test loads the constraints from the architecture specification DSL files and uses the [FCL evaluator implementation](../DSL/constraints) for constraint evaluation). The files specific to each use case contain functions for setting up the initial state of the system (simulation) for testing.

### Running the tests from command line

To run the tests from the terminal, use `pytest generated_adaptations/tests` from the project root directory (`llm-adaptation`).
It might be necessary to add the root directory to the Python path for the imports to work:
Windows: `set PYTHONPATH=%PYTHONPATH%;.`,
Linux: `PYTHONPATH=$PYTHONPATH:.`

### `pytest` options

We use custom formatting of the output of `pytest` as the output is directly used as feedback to the LLM in the vibe coding loop. The [`conftest.py`](./tests/conftest.py) file contains customizations for the test runner and reporting, and the following options are used: `-q` (less verbose output, we could also use `--no-header` instead to remove only platform, rootdir, plugins info), `--tb=no` (remove tracebacks, we could possibly also use `--tb=short` or `--tb=line` as information is in the summary are trimmed if the terminal is not wide enough), `--show-capture=no` (hide simulation `stdout` and `stderr` in the output).
