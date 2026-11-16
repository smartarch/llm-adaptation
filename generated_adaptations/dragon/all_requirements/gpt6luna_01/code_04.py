from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawns_requested = 0
        self._warrior_spawns_requested = 0

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _meal_age(component):
        try:
            return max(0, int(component.steps_since_meal))
        except (AttributeError, TypeError, ValueError):
            return 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        assigned = set()

        def assign(index, group):
            environment.assign_group(components[index], group)
            assigned.add(index)

        farm = getattr(environment, "farm", None)
        try:
            wheat = max(0, int(getattr(farm, "wheat", 0)))
        except (TypeError, ValueError):
            wheat = 0

        # Feed villagers before asking them to spawn or travel. Warriors eat
        # sooner so they can leave for the Cave while still combat-effective.
        for i, component in enumerate(components):
            age = self._meal_age(component)
            if age >= 5 or (
                self._role(component) == "warrior" and age >= 3
            ):
                assign(i, "eat")

        def available_farmer_pair():
            candidates = [
                i for i, component in enumerate(components)
                if i not in assigned
                and self._role(component) == "farmer"
                and self._meal_age(component) < 5
            ]
            return candidates[:2] if len(candidates) >= 2 else []

        # Spawn one farmer first to improve future wheat production.
        if self._farmer_spawns_requested < 1 and wheat >= 10:
            pair = available_farmer_pair()
            if len(pair) == 2:
                for i in pair:
                    assign(i, "spawn farmer")
                wheat -= 10
                self._farmer_spawns_requested += 1

        # Spawn a larger warrior force than the minimum, but leave any
        # unneeded farmers working so the supply of wheat can recover.
        while self._warrior_spawns_requested < 4 and wheat >= 12:
            pair = available_farmer_pair()
            if len(pair) != 2:
                break
            for i in pair:
                assign(i, "spawn warrior")
            wheat -= 12
            self._warrior_spawns_requested += 1

        for i, component in enumerate(components):
            if i in assigned:
                continue
            if self._role(component) == "warrior":
                assign(i, "cave")
            else:
                assign(i, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._role(component) != "warrior":
                environment.assign_group(component, "village")
            elif self._meal_age(component) >= 4:
                # Returning at age 4 leaves time to travel and eat before
                # starvation disables the warrior's damage.
                environment.assign_group(component, "village")
            else:
                environment.assign_group(component, "attack")