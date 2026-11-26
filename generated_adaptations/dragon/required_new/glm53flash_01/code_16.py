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

        # 2) reserve wheat for meals due soon (incl. villagers in the cave)
        upcoming = sum(1 for v in all_vills if v.steps_since_meal >= 3)
        available = wheat - upcoming - 6

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