

Looking at the remaining failures, the core issues are:

1. **Too conservative with wheat reservation** — preventing spawns when warriors are needed
2. **Not aggressive enough about getting attackers in the cave** — gaps in attack coverage let dragon regen 5 HP/step
3. **no_initial_warriors**: must spawn warriors immediately when wheat allows

The key insight: **every attack step prevents 5 HP regen**. Even 1 warrior attacking saves 5 HP. We must minimize gaps and spawn aggressively. I'll simplify the logic, lower wheat thresholds, and send warriors to cave more aggressively.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_v = list(environment.warriors) + list(environment.farmers)
        num_w = len(environment.warriors)
        num_f = len(environment.farmers)

        # Count how many need to eat next step (for reservation)
        meals_next = 0
        for v in all_v:
            if v.steps_since_meal >= 4:
                meals_next += 1  # will be at s_m=5 next step, must eat

        # PHASE 1: Mandatory eat (s_m >= 4 → must eat now)
        eat_set = set()
        for c in components:
            if c.steps_since_meal >= 4:
                if wheat >= 1:
                    environment.assign_group(c, "eat")
                    wheat -= 1
                    eat_set.add(id(c))
                else:
                    # No wheat to eat, but must assign - farm and starve
                    environment.assign_group(c, "farm")
                    eat_set.add(id(c))

        # PHASE 2: Spawn warriors aggressively
        remaining = [c for c in components if id(c) not in eat_set]
        remaining.sort(key=lambda c: 0 if c.role == "Farmer" else 1)

        spawn_set = set()
        # Try to spawn warrior every step if wheat allows
        if wheat >= 12 and len(remaining) >= 2:
            # Reserve enough for meals_next_step
            # Estimate income: ~5 per farmer that will farm after this
            est_farmers_farming = max(1, len([c for c in remaining[2:] if c.role == "Farmer"]))
            est_income = 5 * min(est_farmers_farming, 2) + 2  # +2 for warrior farming
            if wheat - 12 + est_income >= meals_next:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                spawn_set = {id(remaining[0]), id(remaining[1])}
        elif wheat >= 12 and len(remaining) >= 2 and num_w == 0:
            # Desperate: no warriors at all, spawn NOW regardless
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            spawn_set = {id(remaining[0]), id(remaining[1])}

        # PHASE 3: Assign remaining villagers
        remaining = [c for c in components if id(c) not in eat_set and id(c) not in spawn_set]
        farmers_rem = [c for c in remaining if c.role == "Farmer"]
        warriors_rem = [c for c in remaining if c.role == "Warrior"]

        # Count cave occupants
        cave_count = sum(1 for v in all_v if v.location == "Cave")

        for i, c in enumerate(farmers_rem):
            if i == 0:
                environment.assign_group(c, "farm")
            elif i == 1 and num_w >= 3 and cave_count >= 2:
                environment.assign_group(c, "farm")
            elif c.steps_since_meal <= 2 and (num_w <= 2 or cave_count <= 1):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        for c in warriors_rem:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal <= 3 and (cave_count < 2 or num_w <= 2):
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```