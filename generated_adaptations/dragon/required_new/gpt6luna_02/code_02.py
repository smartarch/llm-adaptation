import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_name, group_ids):
        # Group names are the required IDs; use the supplied list when available.
        group_id = group_name if group_name in group_ids else group_name
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        total_population = max(
            1, len(environment.warriors) + len(environment.farmers)
        )
        farmers_total = len(environment.farmers)
        wheat = environment.farm.wheat

        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 4
        ]
        eat_ids = {id(c) for c in eaters}

        # Keep enough farm output to cover the population's approximate meal
        # demand. Increase staffing when the wheat supply is low.
        farm_target = max(1, math.ceil(total_population / 30))
        if wheat < total_population:
            farm_target = max(farm_target, math.ceil(total_population / 10))

        available_farmers = [
            c for c in villagers
            if getattr(c, "role", None) == "Farmer" and id(c) not in eat_ids
        ]
        farm_workers = sorted(
            available_farmers,
            key=lambda c: (
                getattr(c, "hp", 1),
                -getattr(c, "steps_since_meal", 0),
            ),
            reverse=True,
        )[:farm_target]
        farm_ids = {id(c) for c in farm_workers}

        # Spawn only when there is wheat left after reserving for meals and a
        # small buffer. Spawn at most one pair per step.
        cave_due_soon = sum(
            1 for c in environment.warriors + environment.farmers
            if getattr(c, "location", None) == "Cave"
            and getattr(c, "steps_since_meal", 0) >= 3
        )
        meal_reserve = max(
            3, len(eaters) + cave_due_soon + math.ceil(total_population / 6)
        )

        spawn_group = None
        if farmers_total < farm_target:
            spawn_group = "spawn farmer"
            spawn_cost = 10
        else:
            spawn_group = "spawn warrior"
            spawn_cost = 12

        spawn_candidates = [
            c for c in villagers
            if id(c) not in eat_ids and id(c) not in farm_ids
        ]

        # Prefer using spare farmers for spawning, preserving warriors for
        # attacks whenever possible.
        spawn_candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", None) == "Farmer" else 1,
                getattr(c, "hp", 1),
            )
        )

        spawn_ids = set()
        if wheat >= meal_reserve + spawn_cost and len(spawn_candidates) >= 2:
            spawn_ids = {id(spawn_candidates[0]), id(spawn_candidates[1])}

        for c in villagers:
            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = spawn_group
            else:
                group = "cave"
            self._assign(environment, c, group, group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            steps_since_meal = getattr(c, "steps_since_meal", 0)
            hp = getattr(c, "hp", 1)

            # Return early enough to travel home and eat before starvation.
            # Retreating at very low HP also reduces the chance of losing the
            # villager to a Dragon counterattack.
            if steps_since_meal >= 4 or hp <= 1:
                group = "village"
            else:
                group = "attack"

            self._assign(environment, c, group, group_ids)