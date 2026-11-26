from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        total_warriors = sum(1 for w in environment.warriors if w.hp > 0)
        all_vills = list(environment.farmers) + list(environment.warriors)

        # feed everyone who must eat now
        hungry = [c for c in components if c.steps_since_meal >= 4]
        rest = [c for c in components if c.steps_since_meal < 4]

        for c in hungry:
            environment.assign_group(c, "eat")

        # reserve only for meals due in the next ~2 steps
        reserve = sum(1 for v in all_vills if v.steps_since_meal >= 3)
        available = wheat - reserve

        # if we already have enough warriors, go all-in: everyone attacks
        if total_warriors >= 4:
            for c in rest:
                environment.assign_group(c, "cave")
            return

        # otherwise: spawn warriors aggressively while wheat allows
        if available >= 12 and len(rest) >= 2:
            for c in rest[:2]:
                environment.assign_group(c, "spawn warrior")
            rest = rest[2:]
            available -= 12

        if not rest:
            return

        # keep farming if food is tight; otherwise farmers also head to the cave
        if wheat < 15:
            for c in rest:
                environment.assign_group(c, "farm")
        else:
            for c in rest:
                if c.role == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    # keep ~2 farmers working, extra farmers attack
                    environment.assign_group(c, "farm" if wheat < 30 else "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")