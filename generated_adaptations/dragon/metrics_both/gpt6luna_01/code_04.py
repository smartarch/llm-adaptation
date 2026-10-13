from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmers_spawned = 0
        self._warriors_spawned = 0
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

        # Complete the minimum spawn goals, prioritizing Warriors for damage.
        if self._warriors_spawned < 2:
            spawn_group = "spawn warrior"
            cost = 12
        elif self._farmers_spawned < 2:
            spawn_group = "spawn farmer"
            cost = 10
        # Build a larger farming base before relying on frequent Warrior spawns.
        elif len(farmers) < 5 and wheat >= 20:
            spawn_group = "spawn farmer"
            cost = 10
        # With a sufficiently large farming base, use available surplus wheat
        # to keep adding Warriors.
        elif len(farmers) >= 5 and wheat >= 12:
            spawn_group = "spawn warrior"
            cost = 12
        # With a smaller base, wait for a larger reserve before spending wheat.
        elif len(farmers) >= 3 and wheat >= 24:
            spawn_group = "spawn warrior"
            cost = 12
        else:
            return

        if wheat < cost:
            return

        for farmer in farmers[:2]:
            environment.assign_group(farmer, spawn_group)

        if spawn_group == "spawn warrior":
            self._warriors_spawned += 1
        else:
            self._farmers_spawned += 1
        self._last_spawn_step = step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")