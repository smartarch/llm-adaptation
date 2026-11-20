The main improvement is to spend the early wheat on **Warrior** spawns rather than Farmer spawns. The two starting Farmers can alternate between spawning Warriors and producing wheat; as the population grows, the strategy keeps at least one Farmer farming and only spawns when wheat remains above a population-based food reserve. It also keeps Warriors attacking while fed, sends them back early enough to eat safely, and sends Farmers to join the attack once the Dragon is near defeat.

```py
import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_cave_count = 0
        self._final_push = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        dragon_hp = environment.dragon.hp

        if dragon_hp <= 12:
            self._final_push = True

        assignments = {}
        wheat = max(0, environment.farm.wheat)
        total_population = len(villagers) + self._last_cave_count

        # Meals come first; prioritize overdue Warriors, then overdue Farmers.
        meal_order = sorted(
            villagers,
            key=lambda v: (
                -v.steps_since_meal,
                0 if v.role == "Warrior" else 1,
            ),
        )
        for v in meal_order:
            if v.steps_since_meal >= 5 and wheat >= 1:
                assignments[v] = "eat"
                wheat -= 1

        # Warriors in the Village should return to the Cave as soon as fed.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        if self._final_push:
            # At the end, extra damage is more valuable than further production.
            for v in farmers:
                assignments[v] = "cave"
        else:
            # Maintain a food buffer for the growing population. Spawning is
            # worthwhile only when the available wheat is above this reserve.
            reserve = max(5, math.ceil(total_population / 2))
            spawnable_wheat = wheat - reserve

            # Usually keep at least one Farmer working. With just two Farmers,
            # allow both to spawn when the reserve can still be maintained.
            keep_farming = 1 if len(farmers) >= 3 else 0
            usable_farmers = max(0, len(farmers) - keep_farming)
            spawn_pairs = min(usable_farmers // 2, max(0, spawnable_wheat) // 12)

            for v in farmers[:spawn_pairs * 2]:
                assignments[v] = "spawn warrior"
            for v in farmers[spawn_pairs * 2:]:
                assignments[v] = "farm"

        for v in villagers:
            if v not in assignments:
                assignments[v] = "farm"

        for v in villagers:
            environment.assign_group(v, assignments[v])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        self._last_cave_count = len(villagers)

        if environment.dragon.hp <= 12:
            self._final_push = True

        for v in villagers:
            if v.role == "Farmer":
                # Farmers normally support the attack by producing food.
                # Join them in the Cave only for the final push.
                group = "attack" if self._final_push else "village"
            elif v.steps_since_meal >= 4:
                # Travel home now so the Warrior can eat before reaching the
                # starvation threshold, then it will return to the Cave.
                group = "village"
            else:
                group = "attack"

            environment.assign_group(v, group)
```