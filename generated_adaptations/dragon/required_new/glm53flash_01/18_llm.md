Seed 3 likely fails because too many villagers got eaten by the Dragon, leaving too few attackers — we need a bigger, more sustained warrior population. I'll spawn warrior pairs more aggressively (up to 10 warriors, smaller reserve buffer of 5 that still covers due meals, plus per-villager reserves), and let farmers join the attack earlier once food is stable.

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

        # 1) always feed hungry villagers first if wheat allows
        if wheat >= 1:
            for c in hungry:
                plan[c] = "eat"
                wheat -= 1

        # emergency: wheat critically low -> everyone else farms to recover
        if wheat < 6:
            for c in rest:
                plan[c] = "farm"
            for comp, group in plan.items():
                environment.assign_group(comp, group)
            return

        # 2) reserve: meals due soon (incl. cave villagers) + buffer
        upcoming = sum(1 for v in all_vills if v.steps_since_meal >= 3)
        available = wheat - upcoming - 5

        # 3) spawn warrior pairs aggressively (dragon eats villagers, so keep
        #    a large warrior population for sustained DPS)
        while (total_warriors < 10 and available >= 12
               and sum(1 for c in rest if c not in plan) >= 2):
            unassigned = [c for c in rest if c not in plan]
            plan[unassigned[0]] = "spawn warrior"
            plan[unassigned[1]] = "spawn warrior"
            available -= 12
            total_warriors += 1

        # 4) warriors to the cave
        for c in rest:
            if c not in plan and c.role == "Warrior":
                plan[c] = "cave"

        # 5) farmers: farm only if wheat is low; otherwise join the attack
        for c in rest:
            if c not in plan:
                if wheat >= 20 and total_warriors >= 2:
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