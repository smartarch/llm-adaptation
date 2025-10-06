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
