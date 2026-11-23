from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        population = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat

        # Eat while there is still time to travel nowhere: cave villagers
        # are sent home at age 3, then eat on a subsequent Village step.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 4
        ]
        eat_ids = {id(c) for c in eaters}

        # Keep a modest but steady workforce producing food. Scale farm
        # staffing with population, increasing it further if supplies run low.
        target_farmers = max(1, (len(population) + 19) // 20)
        if wheat < 12:
            target_farmers = max(target_farmers, 2)

        farm_candidates = [
            c for c in villagers
            if getattr(c, "role", "") == "Farmer"
            and id(c) not in eat_ids
            and getattr(c, "hp", 0) > 1
        ]
        farm_candidates.sort(
            key=lambda c: (
                getattr(c, "hp", 0),
                -getattr(c, "steps_since_meal", 0),
            ),
            reverse=True,
        )
        farm_ids = {
            id(c) for c in farm_candidates[:target_farmers]
        }

        # Use remaining villagers to recruit as soon as a pair and the
        # required wheat are available. Warriors provide the greatest damage.
        spawn_group = (
            "spawn farmer"
            if len(environment.farmers) == 0
            else "spawn warrior"
        )
        spawn_cost = 10 if spawn_group == "spawn farmer" else 12

        candidates = [
            c for c in villagers
            if id(c) not in eat_ids
            and id(c) not in farm_ids
            and getattr(c, "hp", 0) > 1
        ]
        candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )

        # Keep a small food reserve for imminent meals, but do not hoard wheat.
        imminent_meals = sum(
            1 for c in population
            if getattr(c, "steps_since_meal", 0) >= 4
        )
        spawn_ids = set()
        if wheat >= spawn_cost + imminent_meals and len(candidates) >= 2:
            spawn_ids = {id(candidates[0]), id(candidates[1])}

        for c in villagers:
            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = spawn_group
            elif getattr(c, "hp", 0) <= 1:
                # Avoid exposing critically injured villagers to the Dragon.
                group = "farm"
            else:
                group = "cave"

            environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Returning at age 3 leaves a margin for the trip home and a meal
            # before the starvation limit. Healthy villagers otherwise attack.
            if (
                getattr(c, "steps_since_meal", 0) >= 3
                or getattr(c, "hp", 0) <= 1
            ):
                group = "village"
            else:
                group = "attack"

            environment.assign_group(c, group)