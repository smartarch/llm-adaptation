from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned = {
            "spawn farmer": 0,
            "spawn warrior": 0,
        }
        self._last_spawn_step = None

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if self._role(c) == "farmer"]
        warriors = [c for c in components if self._role(c) == "warrior"]

        # Warriors leave the Village; all Village Farmers remain here.
        for component in warriors:
            environment.assign_group(component, "cave")

        assignments = {}
        for component in farmers:
            assignments[component] = "farm"

        # A spawn needs a pair of villagers and enough wheat. Spawn at most
        # once per step because the observed wheat amount may not update here.
        if len(farmers) >= 2 and self._last_spawn_step != step:
            wheat = getattr(environment.farm, "wheat", 0) or 0
            farmer_deficit = max(0, 2 - self._spawned["spawn farmer"])
            warrior_deficit = max(0, 2 - self._spawned["spawn warrior"])

            spawn_group = None
            if farmer_deficit or warrior_deficit:
                # Balance the initial targets, preferring Farmers on a tie
                # to build up the workforce.
                if farmer_deficit >= warrior_deficit and wheat >= 10:
                    spawn_group = "spawn farmer"
                elif warrior_deficit and wheat >= 12:
                    spawn_group = "spawn warrior"
                elif farmer_deficit and wheat >= 10:
                    spawn_group = "spawn farmer"
            elif (
                getattr(environment.dragon, "hp", 0) > 0
                and len(farmers) >= 4
                and wheat >= 24
            ):
                # Once both minimum targets are met, invest surplus wheat in
                # more Cave damage while retaining Farmers to work the farm.
                spawn_group = "spawn warrior"

            if spawn_group is not None:
                for component in farmers[:2]:
                    assignments[component] = spawn_group
                self._spawned[spawn_group] += 1
                self._last_spawn_step = step

        # Explicitly assign every Village component on every call.
        for component in farmers:
            environment.assign_group(component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._role(component) == "warrior":
                environment.assign_group(component, "attack")
            else:
                # Farmers should stay in the Village and farm or spawn.
                environment.assign_group(component, "village")