The previous policy spent too many steps cycling villagers out of combat and reserved too much wheat, slowing both recruitment and damage. This version keeps farm staffing lean, uses available wheat to recruit warriors, and sends healthy villagers to attack. It also sends cave villagers back early enough to eat before starvation, while keeping critically injured villagers out of combat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        all_villagers = list(environment.warriors) + list(environment.farmers)
        farmers_total = len(environment.farmers)
        wheat = environment.farm.wheat

        # Eat before the six-step limit. Villagers returning from the Cave
        # should be prioritized, since they cannot eat while away.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 5
        ]
        eat_ids = {id(c) for c in eaters}

        # A small farm workforce is usually enough; expand it only when food
        # is scarce. Prefer healthy farmers who are not due to eat.
        total_population = len(all_villagers)
        if wheat < max(5, total_population):
            farm_target = 2
        else:
            farm_target = 1

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
        farm_workers = farm_candidates[:farm_target]
        farm_ids = {id(c) for c in farm_workers}

        # Recruit farmers only if there are none; otherwise favor warriors.
        # Reserve just enough for villagers who must eat this step.
        if farmers_total == 0:
            spawn_group, spawn_cost = "spawn farmer", 10
        elif farmers_total < farm_target and wheat < 5:
            spawn_group, spawn_cost = "spawn farmer", 10
        else:
            spawn_group, spawn_cost = "spawn warrior", 12

        spawn_candidates = [
            c for c in villagers
            if id(c) not in eat_ids
            and id(c) not in farm_ids
            and getattr(c, "hp", 0) > 1
        ]
        # Use farmers for recruitment first where possible, preserving
        # warriors for combat.
        spawn_candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )

        # Do not accumulate a large food reserve: extra wheat is more useful
        # when converted into warriors quickly.
        can_spawn = (
            wheat >= spawn_cost + len(eaters)
            and len(spawn_candidates) >= 2
        )
        spawn_ids = (
            {id(spawn_candidates[0]), id(spawn_candidates[1])}
            if can_spawn else set()
        )

        for c in villagers:
            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = spawn_group
            elif getattr(c, "hp", 0) <= 1:
                # Keep critically injured villagers safely in the Village.
                group = "farm"
            else:
                group = "cave"
            self._assign(environment, c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hp = getattr(c, "hp", 0)
            since_meal = getattr(c, "steps_since_meal", 0)

            # Return with time to travel home and eat before starvation.
            # Retreat at one HP to avoid losing villagers to a counterattack.
            if since_meal >= 4 or hp <= 1:
                group = "village"
            else:
                group = "attack"

            self._assign(environment, c, group)
```