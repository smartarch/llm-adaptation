**Speed improvements:**

1. **Smaller wheat buffer** (10 → 4): less wheat idling, more warrior spawns earlier.
2. **Spawn warriors until we have 8** — more sustained DPS in the Cave, and warriors regenerate losses from dragon attacks.
3. **Farmers join the attack earlier** (wheat ≥ 25 instead of 40) — each farmer still deals 1 damage, and with a tighter buffer farming keeps up anyway.
4. Emergency farm threshold is computed precisely (must cover due meals), so we only farm when truly needed.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        total_warriors = sum(1 for w in environment.warriors if w.hp > 0)
        all_vills = list(environment.farmers) + list(environment.warriors)

        plan = {}

        hungry = [c for c in components if c.steps_since_meal >= 4]
        rest = [c for c in components if c.steps_since_meal < 4]

        # emergency: not enough wheat for due meals -> everyone farms
        if wheat < len(hungry) + 1 or wheat < 8:
            for c in components:
                plan[c] = "farm"
            for comp, group in plan.items():
                environment.assign_group(comp, group)
            return

        # 1) feed the hungry
        for c in hungry:
            plan[c] = "eat"

        # 2) reserve for meals due in the next 2 steps + small buffer
        upcoming = sum(1 for v in all_vills if v.steps_since_meal >= 3)
        available = wheat - len(hungry) - upcoming - 4

        # 3) spawn warrior pairs while wheat allows and we need DPS
        if total_warriors < 8 and available >= 12 and len(rest) >= 2:
            plan[rest[0]] = "spawn warrior"
            plan[rest[1]] = "spawn warrior"
            rest = rest[2:]
            available -= 12

        # 4) warriors to the cave
        for c in rest:
            if c not in plan and c.role == "Warrior":
                plan[c] = "cave"

        # 5) farmers: farm only if wheat is low; otherwise join the attack
        for c in rest:
            if c not in plan:
                if wheat >= 25 and total_warriors >= 2:
                    plan[c] = "cave"
                else:
                    plan[c] = "farm"

        for comp, group in plan.items():
            environment.assign_group(comp, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        plan = {}
        for c in components:
            if c.steps_since_meal >= 4:
                plan[c] = "village"
            else:
                plan[c] = "attack"
        for comp, group in plan.items():
            environment.assign_group(comp, group)
```