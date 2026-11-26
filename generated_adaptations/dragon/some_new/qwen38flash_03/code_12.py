from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        num_w = len(environment.warriors)
        num_f = len(environment.farmers)

        # Phase 1: Villagers with s_m >= 4 MUST eat (never skip)
        eat = [c for c in components if c.steps_since_meal >= 4]
        for c in eat:
            environment.assign_group(c, "eat")

        # Wheat available after eating
        wheat_left = wheat - len(eat)

        # Phase 2: Spawn warriors/farmers from non-eating villagers
        # Parents are NOT consumed - they just skip this step
        non_eat = [c for c in components if c.steps_since_meal < 4]
        # Prefer farmers as spawn parents (keeps warriors free for attacking)
        spawn_order = sorted(non_eat, key=lambda c: 0 if c.role == "Farmer" else 1)

        spawn_set = set()
        # Always try to build warrior army
        if wheat_left >= 12 and len(spawn_order) >= 2:
            environment.assign_group(spawn_order[0], "spawn warrior")
            environment.assign_group(spawn_order[1], "spawn warrior")
            spawn_set = {id(spawn_order[0]), id(spawn_order[1])}
        elif wheat_left >= 10 and num_f < 2 and len(spawn_order) >= 2:
            environment.assign_group(spawn_order[0], "spawn farmer")
            environment.assign_group(spawn_order[1], "spawn farmer")
            spawn_set = {id(spawn_order[0]), id(spawn_order[1])}

        # Phase 3: Assign all remaining villagers to farm or cave
        remaining = [c for c in non_eat if id(c) not in spawn_set]

        # Count farmers assigned so far, keep at least 1 farming for wheat income
        farmers_farmed = 0

        for c in remaining:
            if c.role == "Farmer":
                if farmers_farmed < 1 or num_w >= 3:
                    # Keep farmers farming for wheat
                    environment.assign_group(c, "farm")
                    farmers_farmed += 1
                elif c.steps_since_meal <= 2:
                    # Few warriors: send farmers to attack to prevent dragon regen
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
            else:  # Warrior
                if c.steps_since_meal <= 1:
                    # Fresh warrior: send to cave (arrives s_m<=2, attacks 2-3 steps)
                    environment.assign_group(c, "cave")
                elif num_w <= 1 and c.steps_since_meal <= 3:
                    # Very few warriors: even tired ones must attack
                    environment.assign_group(c, "cave")
                else:
                    # Rest/farm in village, will deploy when fresh
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # MUST leave cave now - 1 step travel means s_m=5 on arrival
                # If we wait, s_m hits 6 next step = HP loss
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")