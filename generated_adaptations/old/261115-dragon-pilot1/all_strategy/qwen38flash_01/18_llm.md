

Looking at the failures, I need to fix:
1. **Wheat tracking**: Must check remaining wheat before each eat/spawn assignment
2. **Unassigned components**: Every component must get exactly one group assignment
3. **Dragon gaps**: Need proper warrior staggering (send 1/step, others eat)
4. **ssm=4 threshold**: Warriors at ssm≥4 must eat in village (ssm=4 → cave → ssm=5 → can't eat → starve)
5. **Cave exit**: Warriors leave cave at ssm≥4

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0
        self._last_send_step = -10

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors ---
        # ssm >= 4: MUST eat (ssm=4 going to cave => arrive ssm=5, no food in cave => ssm=6 starve)
        must_eat_w = [w for w in warriors if w.steps_since_meal >= 4]
        ready_w = [w for w in warriors if w.steps_since_meal < 4]

        for w in must_eat_w:
            if wheat >= 1:
                environment.assign_group(w, "eat")
                wheat -= 1
            else:
                environment.assign_group(w, "farm")

        # Ready warriors: stagger one per step. Highest ssm goes first.
        if ready_w:
            ready_w.sort(key=lambda w: -w.steps_since_meal)
            if step - self._last_send_step >= 1:
                environment.assign_group(ready_w[0], "cave")
                self._last_send_step = step
                for w in ready_w[1:]:
                    if wheat >= 1:
                        environment.assign_group(w, "eat")
                        wheat -= 1
                    else:
                        environment.assign_group(w, "farm")
            else:
                for w in ready_w:
                    if wheat