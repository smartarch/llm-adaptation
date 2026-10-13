I’d remove the large farming targets and wheat reserves: they can postpone combat until too late. This strategy sends Warriors to attack immediately, spends wheat on Warrior spawns as soon as possible, and fulfills the two-Farmer spawn goal along the way. When enough Farmers and wheat are available, it assigns multiple pairs to spawning in one update, leaving at least two Farmers farming. Spawn counters track requests, so they assume a spawn-group assignment successfully triggers a spawn.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _is_warrior(component):
        return "warrior" in str(getattr(component, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        # Warriors leave the Village immediately; Farmers default to farming.
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)
                environment.assign_group(component, "farm")

        if len(farmers) < 2 or getattr(environment.dragon, "hp", 1) <= 0:
            return

        wheat = max(0, getattr(environment.farm, "wheat", 0))
        remaining = len(farmers)
        index = 0

        # Request the minimum Farmer spawns, but do not delay the initial
        # Warrior spawns if there is enough wheat for combat units.
        if self._warrior_spawn_requests == 0 and wheat >= 12:
            spawn_group = "spawn warrior"
            cost = 12
            pair_count = min(remaining // 2, wheat // cost)
            pair_count = min(pair_count, 1)
        elif self._farmer_spawn_requests < 2 and wheat >= 10:
            spawn_group = "spawn farmer"
            cost = 10
            pair_count = 1
        else:
            spawn_group = None
            pair_count = 0

        if pair_count:
            environment.assign_group(farmers[0], spawn_group)
            environment.assign_group(farmers[1], spawn_group)
            index = 2
            remaining -= 2
            wheat -= cost
            if spawn_group == "spawn warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

        # Once the minimum Farmer spawn goal is met, turn surplus wheat and
        # spare Farmer pairs into as many Warrior spawns as possible, while
        # retaining two Farmers to work the farm.
        if self._farmer_spawn_requests >= 2:
            available_pairs = max(0, (remaining - 2) // 2)
            warrior_pairs = min(available_pairs, wheat // 12)

            for _ in range(warrior_pairs):
                environment.assign_group(farmers[index], "spawn warrior")
                environment.assign_group(farmers[index + 1], "spawn warrior")
                index += 2
                wheat -= 12
                self._warrior_spawn_requests += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")
```