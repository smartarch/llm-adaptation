from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)

        farmers_here = [c for c in components if c.role == "Farmer"]
        warriors_here = [c for c in components if c.role == "Warrior"]

        # Eating thresholds per wave (wave A: eat at ssm 5, wave B: at ssm 4,
        # farmers: at ssm 3). All leave a >=1 step margin before starving at 6.
        def eat_threshold(c):
            if c.role == "Warrior":
                return 5 if id(c) % 2 == 0 else 4
            return 3

        hungry = [c for c in components
                  if c.hp <= 1 or c.steps_since_meal >= eat_threshold(c)]
        meal_cost = len(hungry)

        spawn_group, spawn_pair = None, None
        if dragon_alive:
            candidates = [c for c in components if c not in hungry]
            if wheat >= 12 + 10 + meal_cost and len(candidates) >= 2:
                # Prefer converting farmers while keeping >= 2 farmers;
                # otherwise use warriors; emergency: always spawn warriors
                # if none exist at all.
                if not all_warriors:
                    spawn_group, spawn_pair = "spawn warrior", candidates[:2]
                else:
                    pool = [c for c in candidates if c.role == "Farmer"]
                    if len(all_farmers) - 2 >= 2 and len(pool) >= 2:
                        spawn_group, spawn_pair = "spawn warrior", pool[:2]
                    elif len(warriors_here) >= 2:
                        spawn_group, spawn_pair = "spawn warrior", \
                            [c for c in candidates if c.role == "Warrior"][:2]
                    elif len(pool) >= 2:
                        spawn_group, spawn_pair = "spawn warrior", pool[:2]
            if spawn_group is None and len(all_farmers) <= 1 \
                    and wheat >= 10 + 10 + meal_cost:
                pool = [c for c in candidates if c.role == "Farmer"]
                if len(pool) >= 2:
                    spawn_group, spawn_pair = "spawn farmer", pool[:2]

        spawned = set(id(c) for c in (spawn_pair or []))

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_group)
            elif c in hungry:
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                # Just fed -> head to the Cave; otherwise wait/farm until
                # the eat threshold of this wave comes due.
                if c.steps_since_meal == 0:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
            elif (c.role == "Farmer" and dragon_alive and c.steps_since_meal == 0
                  and len(farmers_here) >= 2 and wheat >= 15
                  and len(all_warriors) <= 2):
                # Spare farmer joins a raid for extra early pressure
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Wave A: 3 attacks (ssm 1-3), return at ssm 4, eat at 5.
                # Wave B: 2 attacks (ssm 1-2), return at ssm 3, eat at 4.
                # The phase shift keeps the Dragon under near-continuous attack.
                limit = 3 if id(c) % 2 == 0 else 2
                if c.hp <= 1 or c.steps_since_meal > limit:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            else:
                # Farmers raid lightly: 1 attack, then home (eat at ssm 3)
                if c.hp <= 1 or c.steps_since_meal >= 2:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")