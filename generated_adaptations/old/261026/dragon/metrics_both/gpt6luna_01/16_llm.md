The earlier strategies could spend wheat as soon as it reached the spawn cost, leaving too little reserve to keep the economy going. This version keeps a 12-wheat reserve for combat spawns, requests two of each villager type, and then uses surplus wheat for Warriors. It sends Warriors to the Cave and assigns them to attack on every update; Farmers default to farming unless a pair is selected to spawn.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0
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

        wheat = max(0, getattr(environment.farm, "wheat", 0))

        # Request the minimum combat force early, while also meeting the
        # requirement to add Farmers. Afterward, spend only surplus wheat on
        # more Warriors, preserving a small reserve for the farm economy.
        if self._warrior_spawn_requests < 2:
            spawn_group, cost = "spawn warrior", 12
        elif self._farmer_spawn_requests < 2:
            spawn_group, cost = "spawn farmer", 10
        elif wheat >= 24:
            spawn_group, cost = "spawn warrior", 12
        else:
            return

        if wheat < cost:
            return

        environment.assign_group(farmers[0], spawn_group)
        environment.assign_group(farmers[1], spawn_group)

        if spawn_group == "spawn warrior":
            self._warrior_spawn_requests += 1
        else:
            self._farmer_spawn_requests += 1
        self._last_spawn_step = step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")
```