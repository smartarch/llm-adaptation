The earlier versions limited recruitment to one pair per step and sent villagers home too early, reducing damage output. This policy recruits as many warrior pairs as the available wheat and villagers allow, while keeping a modest farm workforce. Cave villagers return at meal age 4, leaving time to reach the Village and eat before the starvation limit; otherwise they attack until critically injured.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        all_villagers = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat

        # Eat at age 4 to leave a margin for travel and avoid starvation.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 4
        ]
        eat_ids = {id(c) for c in eaters}

        # A farmer produces 5 wheat per step, enough for roughly 30 villagers'
        # average meal consumption. Maintain a small workforce, expanding it
        # when the stock is nearly depleted.
        population = len(all_villagers)
        farm_target = max(1, (population + 29) // 30)
        if wheat < 8:
            farm_target = max(farm_target, 2)

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

        # If there are no farmers, recruit farmers first. Otherwise use the
        # available wheat to recruit warriors, assigning as many complete
        # pairs as the stock can support.
        if len(environment.farmers) == 0:
            spawn_group = "spawn farmer"
            spawn_cost = 10
        else:
            spawn_group = "spawn warrior"
            spawn_cost = 12

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

        # Leave wheat for villagers who must eat this step; spend the rest on
        # complete recruitment pairs.
        meal_reserve = len(eaters)
        pairs_affordable = max(0, (wheat - meal_reserve) // spawn_cost)
        pairs_available = len(spawn_candidates) // 2
        spawn_count = 2 * min(pairs_affordable, pairs_available)
        spawn_ids = {id(c) for c in spawn_candidates[:spawn_count]}

        for c in villagers:
            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = spawn_group
            elif getattr(c, "hp", 0) <= 1:
                group = "farm"
            else:
                group = "cave"

            environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # A return at meal age 4 allows the villager to reach the Village
            # before the six-step starvation limit.
            if (
                getattr(c, "steps_since_meal", 0) >= 4
                or getattr(c, "hp", 0) <= 1
            ):
                group = "village"
            else:
                group = "attack"

            environment.assign_group(c, group)
```