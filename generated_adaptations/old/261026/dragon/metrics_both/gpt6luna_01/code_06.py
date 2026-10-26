from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0
        self._last_spawn_step = -1

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

        if len(farmers) < 2 or step == self._last_spawn_step:
            return
        if getattr(environment.dragon, "hp", 1) <= 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)
        spawn_group = None
        cost = 0

        # Get Warriors into the fight early, but grow the farming workforce
        # before repeatedly spending wheat on combat units.
        if self._warrior_spawn_requests < 2:
            spawn_group, cost = "spawn warrior", 12
        elif len(farmers) < 6:
            spawn_group, cost = "spawn farmer", 10
        elif wheat >= 12:
            spawn_group, cost = "spawn warrior", 12

        if spawn_group is None or wheat < cost:
            return

        # Assign exactly a pair to the spawn group; all other Farmers remain
        # explicitly assigned to farm.
        for farmer in farmers[:2]:
            environment.assign_group(farmer, spawn_group)

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