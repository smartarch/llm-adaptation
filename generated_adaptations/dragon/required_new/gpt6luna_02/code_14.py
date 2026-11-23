from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        population = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Feed immediately upon return when the meal clock is getting high.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 4
        ]
        eat_ids = {id(c) for c in eaters}

        # Preserve a farmer only when supplies need replenishing. With a
        # healthy stock, those villagers are more valuable in the Cave.
        farm_ids = set()
        if wheat < max(6, len(population) // 2):
            farm_candidates = [
                c for c in villagers
                if id(c) not in eat_ids
                and getattr(c, "role", "") == "Farmer"
                and getattr(c, "hp", 0) > 0
            ]
            if farm_candidates:
                farm_candidates.sort(
                    key=lambda c: (
                        getattr(c, "hp", 0),
                        -getattr(c, "steps_since_meal", 0),
                    ),
                    reverse=True,
                )
                farm_ids.add(id(farm_candidates[0]))

        # Recruit a farmer if none exist; otherwise recruit warriors early,
        # while wheat is plentiful and the Dragon still has substantial HP.
        if len(environment.farmers) == 0:
            spawn_group, spawn_cost = "spawn farmer", 10
        else:
            spawn_group, spawn_cost = "spawn warrior", 12

        due_meals = sum(
            1 for c in population
            if getattr(c, "steps_since_meal", 0) >= 4
        )
        candidates = [
            c for c in villagers
            if id(c) not in eat_ids
            and id(c) not in farm_ids
            and getattr(c, "hp", 0) > 0
        ]
        candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )

        spawn_ids = set()
        if (
            dragon_hp > 15
            and wheat >= spawn_cost + due_meals
            and len(candidates) >= 2
        ):
            spawn_ids = {id(candidates[0]), id(candidates[1])}

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
            # Leaving at age 4 gives time to travel home and eat before
            # starvation begins. Otherwise every able villager attacks.
            if getattr(c, "steps_since_meal", 0) >= 4:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(c, group)