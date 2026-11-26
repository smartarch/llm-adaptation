from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assignments = [None] * len(villagers)
        wheat = max(0, environment.farm.wheat)

        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        population = warriors + farmers

        # Feed the most urgent villagers first. Feeding at counter 4 also
        # gives village workers some margin against future food shortages.
        due = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 4),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in due:
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        # Keep food for cave villagers approaching their return trip.
        cave_reserve = sum(
            1 for v in population
            if v.location == "Cave" and v.steps_since_meal >= 3
        )

        # Feed warriors at counter 3 so they can start a fresh cave trip
        # on the following step.
        for i, v in enumerate(villagers):
            if (
                assignments[i] is None
                and v.role == "Warrior"
                and v.steps_since_meal == 3
                and wheat > cave_reserve + 2
            ):
                assignments[i] = "eat"
                wheat -= 1

        # Reserve food for villagers who will soon need a meal.
        reserve = 2 + cave_reserve + sum(
            1 for i, v in enumerate(villagers)
            if assignments[i] is None and v.steps_since_meal >= 3
        )

        available = [
            i for i in range(len(villagers))
            if assignments[i] is None
        ]

        # Spawn warriors while they still have time to contribute.
        # Prefer farmers as parents so existing warriors can keep fighting.
        target_warriors = 8
        needed = max(0, target_warriors - len(warriors))
        if step < 20 and needed and len(available) >= 2:
            candidates = sorted(
                available,
                key=lambda i: (
                    villagers[i].role != "Farmer",
                    -villagers[i].steps_since_meal,
                ),
            )

            # If there are at least three available farmers, keep one
            # working rather than using every farmer for spawning.
            available_farmers = [
                i for i in candidates if villagers[i].role == "Farmer"
            ]
            if len(available_farmers) >= 3:
                candidates.remove(available_farmers[-1])

            affordable = max(0, int((wheat - reserve) // 12))
            pairs = min(needed, affordable, len(candidates) // 2)
            for i in candidates[:2 * pairs]:
                assignments[i] = "spawn warrior"
            wheat -= 12 * pairs

        # Keep a farmer producing food when reserves are low. Spare farmers
        # join the attack once the economy has had time to develop.
        remaining_farmers = [
            i for i, v in enumerate(villagers)
            if assignments[i] is None and v.role == "Farmer"
        ]
        protected_farmer = None
        food_buffer = len(population) + 3
        if remaining_farmers and wheat < food_buffer:
            protected_farmer = min(
                remaining_farmers,
                key=lambda i: villagers[i].steps_since_meal,
            )

        for i, v in enumerate(villagers):
            if assignments[i] is not None:
                continue

            ready_for_trip = v.steps_since_meal <= 2
            if v.role == "Warrior" and ready_for_trip:
                assignments[i] = "cave"
            elif (
                v.role == "Farmer"
                and i != protected_farmer
                and ready_for_trip
                and (
                    step >= 12
                    or environment.dragon.hp <= 20
                )
            ):
                assignments[i] = "cave"
            else:
                assignments[i] = "farm"

        for villager, group in zip(villagers, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            # At counter 4, return now so the villager can eat in time.
            if villager.steps_since_meal >= 4:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(villager, group)