from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        population = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat

        # Eat before going back to the Cave; a villager returning from the
        # Cave at age 4 arrives at age 5 and can eat on its next Village turn.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 5
        ]
        eat_ids = {id(c) for c in eaters}

        farm_ids = set()
        farmers = [
            c for c in villagers
            if getattr(c, "role", "") == "Farmer"
            and id(c) not in eat_ids
        ]

        # Keep food production alive when the wheat reserve is low. Prefer
        # one farmer rather than diverting a large fraction of the force.
        if farmers and wheat < max(8, len(population)):
            farmer = max(farmers, key=lambda c: getattr(c, "hp", 0))
            farm_ids.add(id(farmer))

        spawn_group = "spawn farmer" if len(environment.farmers) == 0 else "spawn warrior"
        spawn_cost = 10 if spawn_group == "spawn farmer" else 12

        # Reserve food only for villagers who must eat now. Spend excess wheat
        # on as many complete spawn pairs as can be assigned this step.
        candidates = [
            c for c in villagers
            if id(c) not in eat_ids
            and id(c) not in farm_ids
        ]
        candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )

        reserve = len(eaters)
        pairs = min(
            len(candidates) // 2,
            max(0, (wheat - reserve) // spawn_cost),
        )
        spawn_ids = {id(c) for c in candidates[: 2 * pairs]}

        for c in villagers:
            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = spawn_group
            else:
                group = "cave"
            environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Retreat at age 4 so travel home does not push the villager past
            # the six-step meal interval. Otherwise keep attacking, including
            # at low HP, since wounded villagers still deal full damage.
            if getattr(c, "steps_since_meal", 0) >= 4:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(c, group)