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
        assigned = set()

        # 1) MANDATORY EATING: s_m >= 4 means must eat now (travel takes 1 step)
        #    Sort by s_m descending so most urgent eat first
        eaters = sorted(
            [c for c in components if c.steps_since_meal >= 4],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in eaters:
            if wheat >= 1:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                # No wheat available; farm and start starving (survive on HP)
                environment.assign_group(c, "farm")
            assigned.add(id(c))

        # 2) SPAWNING: build warrior army aggressively
        non_assigned = [c for c in components if id(c) not in assigned]
        # Prefer farmers as spawn parents to keep warriors free for attacking
        non_assigned.sort(key=lambda c: 0 if c.role == "Farmer" else 1)

        # Spawn warrior if we have wheat and 2+ villagers available
        # Also spawn farmer if we have very few farmers
        if wheat >= 12 and len(non_assigned) >= 2:
            environment.assign_group(non_assigned[0], "spawn warrior")
            environment.assign_group(non_assigned[1], "spawn warrior")
            wheat -= 12
            assigned.add(id(non_assigned[0]))
            assigned.add(id(non_assigned[1]))
        elif wheat >= 10 and num_f < 2 and len(non_assigned) >= 2:
            environment.assign_group(non_assigned[0], "spawn farmer")
            environment.assign_group(non_assigned[1], "spawn farmer")
            wheat -= 10
            assigned.add(id(non_assigned[0]))
            assigned.add(id(non_assigned[1]))

        # 3) FARMING: need at least 1 farmer to produce wheat
        #    1 farmer = 5 wheat/step; ~0.2 wheat/villager/step consumption
        #    So 1 farmer sustains ~25 villagers easily
        min_farming = 1 if num_f >= 1 else 0
        farm_count = 0

        # 4) DEPLOY warriors to cave when fresh; farmers farm
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Farmer":
                if farm_count < max(1, min(2, num_f - 2)):
                    # Keep enough farmers farming for wheat income
                    environment.assign_group(c, "farm")
                    farm_count += 1
                elif num_w <= 2 and c.steps_since_meal <= 2:
                    # Emergency: send extra farmers to attack to prevent regen
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
                    farm_count += 1
            else:  # Warrior
                if c.steps_since_meal <= 1:
                    environment.assign_group(c, "cave")
                elif num_w <= 1 and c.steps_since_meal <= 3:
                    # Desperate: even tired warriors must attack
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
            assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # MUST leave now: travel=1 step, arrive at village s_m=5, eat s_m=0
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")