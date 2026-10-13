The previous approach tried to assign several spawn pairs in one update and inferred progress from those assignments. If a spawn does not resolve immediately, that can overcount progress and starve the farm. This version requests at most one spawn per update, prioritizes the minimum Warrior and Farmer spawn goals, then uses available wheat to add Warriors. All other Farmers keep farming, and Warriors in the Cave are always assigned to attack.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawns_requested = 0
        self._farmer_spawns_requested = 0
        self._last_spawn_step = None

    @staticmethod
    def _is_warrior(component):
        return "warrior" in str(getattr(component, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)
                environment.assign_group(component, "farm")

        if len(farmers) < 2 or self._last_spawn_step == step:
            return
        if getattr(environment.dragon, "hp", 1) <= 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)

        # Meet the minimum spawn goals, prioritizing combat strength.
        if self._warrior_spawns_requested < 2:
            spawn_group, cost = "spawn warrior", 12
        elif self._farmer_spawns_requested < 2:
            spawn_group, cost = "spawn farmer", 10
        # After the minimum goals, turn spare wheat into more attackers.
        elif wheat >= 12:
            spawn_group, cost = "spawn warrior", 12
        else:
            return

        if wheat < cost:
            return

        # Assign exactly one pair to spawning; explicitly leave everyone else
        # assigned to the farm.
        environment.assign_group(farmers[0], spawn_group)
        environment.assign_group(farmers[1], spawn_group)

        if spawn_group == "spawn warrior":
            self._warrior_spawns_requested += 1
        else:
            self._farmer_spawns_requested += 1
        self._last_spawn_step = step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")
```