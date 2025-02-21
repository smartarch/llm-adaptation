# Strategy Generation

## Generate prompts


Run `../main.py` with the following arguments for Farm:

```txt
farm/configs/default.yaml farm/configs/config_no_battery.yaml generated_adaptations/jinja_prompt_generator.yaml DSL/drones.yaml
````

Variants for farm:

* `farm/configs/simulation_description_1.yaml`
* `farm/configs/strategy.yaml`
* `farm/configs/goal_step_by_step.yaml`

## Run

```bash
python run_generated.py
```
