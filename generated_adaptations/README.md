# Offline prompting

## Dragon

### Prompt

[prompts/dragon_strategy.md](prompts/dragon_strategy.md) - only with strategy

save it as `01_01_user.md` in the folder

### Tested variants

example is selected by the parent folder: `dragon`

* without unit tests: `generator.py --retries_test=0`
  * parent folder: `dragon_notest`
* with only system constraints: `generator.py --retries_test=3`
  * config `DSL/dragon.yaml`
  * parent folder: `dragon`
* with user constraints: `generator.py --retries_test=3`
  * config `DSL/dragon.yaml` + `DSL/dragon_constraints.yaml`
  * parent folder: `dragon_constraints`



To run the tests from the terminal, use `pytest generated_adaptations/tests` from the project root directory (`llm-adaptation`).
It might be necessary to add the root directory to the Python path for the imports to work:
Windows: `set PYTHONPATH=%PYTHONPATH%;.`,
Linux: `PYTHONPATH=$PYTHONPATH:.`

Options: `-q` (less verbose output, we could also use `--no-header` instead to remove only platform, rootdir, plugins info), `--tb=no` (remove tracebacks, we could possibly also use `--tb=short` or `--tb=line` as information is in the summary are trimmed if the terminal is not wide enough), `--show-capture=no` (hide simulation `stdout` and `stderr` in the output).

Example: `pytest generated_adaptations/tests -q --tb=no --example=farm --adaptation_name=4o_sd2_4`