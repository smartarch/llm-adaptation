from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initial_farmers = None
        self._farmer_spawn_requests = 0
        self._warrior_spawn_requests = 0
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

        if self._initial_farmers is None:
            self._initial_farmers = len(farmers)

        if len(farmers) < 2 or self._last_spawn_step == step:
            return
        if getattr(environment.dragon, "hp", 1) <= 0:
            return

        wheat = max(0, getattr(environment.farm, "wheat", 0))

        if self._warrior_spawn_requests < 2:
            spawn_group, cost = "spawn warrior", 12
        else:
            # Ensure at least two Farmers are spawned and build the farming
            # population toward six before prioritizing further Warriors.
            farmer_target = max(2, 6 - self._initial_farmers)
            if self._farmer_spawn_requests < farmer_target:
                spawn_group, cost = "spawn farmer", 10
            elif wheat >= 12:
                spawn_group, cost = "spawn warrior", 12
            else:
                return

        if wheat < cost:
            return

        # One pair spawns per update; every other Farmer remains assigned to farm.
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