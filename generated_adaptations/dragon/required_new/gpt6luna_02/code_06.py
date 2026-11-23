from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        population = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        warrior_count = len(environment.warriors)
        farmer_count = len(environment.farmers)

        # Feed before the six-step starvation limit.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 4
        ]
        eat_ids = {id(c) for c in eaters}

        # One healthy farmer usually produces enough food for a small group.
        # Add another when the food supply is running low.
        farm_target = 1
        if wheat < max(4, len(population)):
            farm_target = 2

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
        farm_ids = {id(c) for c in farm_candidates[:farm_target]}

        # Build an early fighting force, but avoid spending the last food on
        # recruitment. Stop recruiting once the force is already substantial
        # or the Dragon is nearly defeated.
        if farmer_count == 0:
            spawn_group, spawn_cost = "spawn farmer", 10
        else:
            spawn_group, spawn_cost = "spawn warrior", 12

        spawn_candidates = [
            c for c in villagers
            if id(c) not in eat_ids
            and id(c) not in farm_ids
            and getattr(c, "hp", 0) > 1
        ]
        spawn_candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )

        reserve = len(eaters)
        should_spawn = (
            warrior_count < 8
            and dragon_hp > 12
            and wheat >= spawn_cost + reserve
            and len(spawn_candidates) >= 2
        )
        spawn_ids = set()
        if should_spawn:
            spawn_ids = {
                id(spawn_candidates[0]),
                id(spawn_candidates[1]),
            }

        for c in villagers:
            since_meal = getattr(c, "steps_since_meal", 0)

            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = spawn_group
            elif getattr(c, "hp", 0) <= 1:
                # Keep badly injured villagers out of the Dragon's reach.
                group = "farm"
            elif since_meal >= 3:
                # Eating here avoids sending a villager on a round trip that
                # would leave too little time to attack safely.
                group = "eat"
            else:
                group = "cave"

            environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            since_meal = getattr(c, "steps_since_meal", 0)
            hp = getattr(c, "hp", 0)

            # Returning at four steps leaves time to travel to the Village
            # and eat before starvation. HP does not regenerate, so retreat
            # critically injured villagers rather than exposing them to hits.
            if since_meal >= 4 or hp <= 1:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(c, group)