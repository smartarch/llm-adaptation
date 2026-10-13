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

        if (
            len(farmers) < 2
            or self._last_spawn_step == step
            or getattr(environment.dragon, "hp", 1) <= 0
        ):
            return

        wheat = max(0, getattr(environment.farm, "wheat", 0))

        if self._warrior_spawns_requested < 2:
            spawn_group, cost = "spawn warrior", 12
        elif self._farmer_spawns_requested < 2:
            spawn_group, cost = "spawn farmer", 10
        elif wheat >= 12:
            spawn_group, cost = "spawn warrior", 12
        else:
            return

        if wheat < cost:
            return

        # Use one pair per update; all other Farmers remain assigned to farm.
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