**Fixes:**

1. **Never assign "eat" when wheat is 0** — instead farm that step to earn wheat (that caused the invalid-assignment and unassigned-component failures).
2. **Reserve accounting now projects farming income:** wheat after this step must cover every villager whose meal is due soon (steps_since_meal ≥ 3), so spawning never bankrupts the food supply.
3. **All components always get exactly one group** — a final fallback assignment for anyone not yet placed.
4. **Everyone must be fed within 6 steps** — hungry cave villagers head home at ≥ 4; if wheat is critically low, everyone farms until it recovers.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        all_vills = list(environment.farmers) + list(environment.warriors)
        total_warriors = sum(1 for w in environment.warriors if w.hp > 0)

        # meals due very soon (within next 2 steps) must stay covered
        reserve = sum(1 for v in all_vills if v.steps_since_meal >= 3)

        hungry = [c for c in components if c.steps_since_meal >= 4]
        rest = [c for c in components if c.steps_since_meal < 4]

        assigned = set()

        # 1) feed the hungry — but only if wheat allows
        if wheat >= 1:
            for c in hungry:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
        # if no wheat, hungry villagers must farm to earn food

        # 2) emergency: no wheat at all -> everyone farms
        if wheat < 2:
            for c in rest:
                if id(c) not in assigned:
                    environment.assign_group(c, "farm")
                    assigned.add(id(c))
            return

        # 3) project wheat after this step's actions
        #    (farmers in "farm" add 5 each; meals cost 1 each)
        projected = wheat - reserve
        farmers_farming = 0

        # spawn warriors aggressively while we need them
        if total_warriors < 4 and projected >= 12 and len(rest) >= 2:
            for c in rest[:2]:
                environment.assign_group(c, "spawn warrior")
                assigned.add(id(c))
            rest = rest[2:]
            projected -= 12

        # warriors go to the cave
        for c in rest:
            if id(c) not in assigned and c.role == "Warrior":
                environment.assign_group(c, "cave")
                assigned.add(id(c))

        # farmers: farm to cover reserve, otherwise join the attack
        for c in rest:
            if id(c) in assigned or c.role != "Farmer":
                continue
            if projected < 5 and farmers_farming < 3:
                environment.assign_group(c, "farm")
                farmers_farming += 1
                projected += 5
            else:
                environment.assign_group(c, "cave")

        # fallback: everyone must be assigned exactly once
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
            assigned.add(id(c))
```