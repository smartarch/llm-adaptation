The failures come from cave villagers: when wheat runs low, the emergency "everyone farms" branch starves villagers arriving from the Cave (they get farmed instead of fed even though wheat ≥ 1), and the tight buffer drains wheat below what's needed for returning villagers. Fixes:

1. **Always feed hungry villagers if at least 1 wheat exists** — the emergency branch only farms the *rest*, not the hungry.
2. **Raise the reserve buffer back to 8** and count cave villagers' due meals in the reserve so their return trips are covered.
3. **Return cave villagers home earlier** (threshold 3) to absorb the one-step travel time safely.

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

        # 1) always feed hungry villagers if wheat allows (highest priority)
        fed = 0
        if wheat >= 1:
            for c in hungry:
                plan[c] = "eat"
                fed += 1
                wheat -= 1

        # emergency: wheat critically low -> everyone else farms to recover
        if wheat < 8:
            for c in rest:
                plan[c] = "farm"
            for comp, group in plan.items():
                environment.assign_group(comp, group)
            return

        # 2) reserve wheat for ALL meals due soon (incl. villagers in the cave)
        upcoming = sum(1 for v in all_vills if v.steps_since_meal >= 3)
        available = wheat - upcoming - 8

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
            if c.steps_since_meal >= 3:
                plan[c] = "village"
            else:
                plan[c] = "attack"
        for comp, group in plan.items():
            environment.assign_group(comp, group)
```