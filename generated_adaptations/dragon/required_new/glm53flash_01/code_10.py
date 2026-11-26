from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        total_warriors = sum(1 for w in environment.warriors if w.hp > 0)
        all_vills = list(environment.farmers) + list(environment.warriors)

        # plan: component -> group; built fully before assigning
        plan = {}

        hungry = [c for c in components if c.steps_since_meal >= 4]
        rest = [c for c in components if c.steps_since_meal < 4]

        # emergency: not enough wheat for the due meals -> everyone farms
        if wheat < len(hungry) + 1 or wheat < 10:
            for c in components:
                plan[c] = "farm"
            for comp, group in plan.items():
                environment.assign_group(comp, group)
            return

        # 1) feed the hungry
        for c in hungry:
            plan[c] = "eat"

        # 2) reserve wheat for meals due soon + buffer
        upcoming = sum(1 for v in all_vills if v.steps_since_meal >= 3)
        available = wheat - len(hungry) - upcoming - 10

        # 3) spawn warrior pairs while we need them and wheat allows
        if total_warriors < 6 and available >= 12 and len(rest) >= 2:
            plan[rest[0]] = "spawn warrior"
            plan[rest[1]] = "spawn warrior"
            rest = rest[2:]
            available -= 12

        # 4) warriors to the cave
        for c in rest:
            if c not in plan and c.role == "Warrior":
                plan[c] = "cave"

        # 5) farmers: farm unless wheat is plentiful and we have attackers
        for c in rest:
            if c not in plan:
                if wheat >= 40 and total_warriors >= 2:
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