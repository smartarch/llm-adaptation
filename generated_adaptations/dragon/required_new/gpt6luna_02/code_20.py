from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        population = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat
        farmers_total = len(environment.farmers)

        # Eat while safely in the Village. A villager returning from the
        # Cave at age 4 or 5 must be fed before being sent out again.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 4
        ]
        eat_ids = {id(c) for c in eaters}

        # Keep the minimum food production needed to replenish supplies.
        farm_target = max(1, (len(population) + 29) // 30)
        if wheat < 12:
            farm_target = max(farm_target, 2)

        farmers_here = [
            c for c in villagers
            if getattr(c, "role", "") == "Farmer"
            and id(c) not in eat_ids
        ]
        farmers_here.sort(
            key=lambda c: (
                getattr(c, "hp", 0),
                -getattr(c, "steps_since_meal", 0),
            ),
            reverse=True,
        )
        farm_ids = {id(c) for c in farmers_here[:farm_target]}

        # Recruit warrior pairs whenever wheat permits. If there are no
        # farmers at all, recruit a farmer first so food production can resume.
        spawn_group = "spawn farmer" if farmers_total == 0 else "spawn warrior"
        spawn_cost = 10 if spawn_group == "spawn farmer" else 12

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

        # Reserve food for meals due now; spend the remaining stock on as
        # many full pairs as the Village population can support.
        meal_reserve = len(eaters)
        pairs_by_food = max(0, (wheat - meal_reserve) // spawn_cost)
        pairs_by_people = len(candidates) // 2
        spawn_count = 2 * min(pairs_by_food, pairs_by_people)
        spawn_ids = {id(c) for c in candidates[:spawn_count]}

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
            age = getattr(c, "steps_since_meal", 0)
            role = getattr(c, "role", "")

            # Stagger trips back so farmers and warriors do not all leave
            # the Cave at once. Returning at these ages leaves a margin for
            # the trip home and a meal before six consecutive steps pass.
            return_age = 3 if role == "Farmer" else 4
            if age >= return_age:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(c, group)