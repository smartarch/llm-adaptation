import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = len(environment.warriors) + len(environment.farmers)

        # Bucket each component into exactly one group
        must_eat = []            # ssm >= 4: critical, eat NOW (or farm if no wheat)
        warrior_eat = []         # warriors with ssm == 2 or 3: eat to reset cycle
        to_cave = []             # warriors with ssm <= 1: send to cave
        spare = []               # farmers with ssm <= 3 (not urgent)

        for c in components:
            if c.steps_since_meal >= 4:
                must_eat.append(c)
            elif c.role == "Warrior" and c.steps_since_meal >= 2:
                warrior_eat.append(c)
            elif c.role == "Warrior":
                to_cave.append(c)
            else:
                spare.append(c)

        eat_count = 0

        # Critical eaters: eat if wheat, else farm to produce
        for c in must_eat:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                environment.assign_group(c, "farm")

        # Warriors needing food: eat to reset for a 3-attack cycle
        for c in warrior_eat:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                # No wheat: farm (don't send to cave - would waste a trip)
                environment.assign_group(c, "farm")

        # Fresh warriors go to cave
        for w in to_cave:
            if w.hp <= 1:
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        # Spare farmers: consider spawning warriors, rest farm
        # Count how many villagers will need to eat soon (next ~3 steps)
        upcoming_meals = 0
        for v in environment.warriors + environment.farmers:
            if v.steps_since_meal >= 3:
                upcoming_meals += 1

        # Farming output this step (farmers NOT spawning and NOT eating)
        farm_count_after = len(spare) - (2 if len(spare) >= 2 else 0)
        farm_output = 5 * farm_count_after

        # Estimate wheat after this step: current - meals_this_step - spawn_cost + farm_output
        # Need: result >= upcoming_meals (next few steps)
        after_meals = wheat - eat_count

        can_spawn_warrior = False
        if len(spare) >= 2:
            after_spawn = after_meals - 12 + farm_output
            # Keep at least 1 reserve beyond upcoming meals for safety
            if after_spawn >= upcoming_meals + 1:
                # Always try to grow warriors toward 8; critical if 0
                if total_warriors == 0:
                    can_spawn_warrior = True
                elif total_warriors < 8:
                    can_spawn_warrior = True

        idx = 0
        if can_spawn_warrior and len(spare) >= 2:
            environment.assign_group(spare[0], "spawn warrior")
            environment.assign_group(spare[1], "spawn warrior")
            idx = 2

        # Remaining spare farmers farm
        for i in range(idx, len(spare)):
            environment.assign_group(spare[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Must leave: travel 1 step → arrive village ssm=5 → eat that step (before ssm=6)
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")