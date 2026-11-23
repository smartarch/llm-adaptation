The earlier policy could spend wheat on recruitment just before many villagers needed meals, and it sometimes pulled injured fighters out of combat. This version reserves food for imminent meals, maintains a small farm workforce, and recruits at most one warrior per step when two villagers can be spared. Healthy cave villagers keep attacking and return at meal age 4 so they can eat in the Village before reaching six consecutive steps without food.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        population = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Eat before the starvation limit. A villager returning from the Cave
        # at meal age 4 will be in the Village in time to eat at age 5.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 5
        ]
        eat_ids = {id(c) for c in eaters}

        # Keep enough production to sustain meals as the population grows.
        # One farmer produces 5 wheat per step; approximately one per 30
        # villagers covers average food consumption.
        farm_target = max(1, (len(population) + 29) // 30)
        if wheat < 5:
            farm_target += 1

        farm_candidates = [
            c for c in villagers
            if id(c) not in eat_ids and getattr(c, "hp", 0) > 0
        ]
        farm_candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )
        farm_workers = farm_candidates[:farm_target]
        farm_ids = {id(c) for c in farm_workers}

        # Reserve meals for anyone already due or returning from the Cave.
        imminent_meals = sum(
            1 for c in population
            if getattr(c, "steps_since_meal", 0) >= 4
        )

        # Spawn warriors early, but stop recruiting when the Dragon is close
        # to death. One pair per step limits lost combat time and food shocks.
        spawn_candidates = [
            c for c in villagers
            if id(c) not in eat_ids
            and id(c) not in farm_ids
            and getattr(c, "hp", 0) > 0
        ]
        spawn_candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )

        spawn_ids = set()
        if (
            dragon_hp > 18
            and wheat >= 12 + imminent_meals
            and len(spawn_candidates) >= 2
        ):
            spawn_ids = {id(spawn_candidates[0]), id(spawn_candidates[1])}

        for c in villagers:
            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = "spawn warrior"
            else:
                group = "cave"

            environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Return with enough time to travel to the Village and eat before
            # the six-step starvation threshold. Otherwise keep attacking:
            # low HP alone is not a reason to sacrifice combat turns.
            if getattr(c, "steps_since_meal", 0) >= 4:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(c, group)
```