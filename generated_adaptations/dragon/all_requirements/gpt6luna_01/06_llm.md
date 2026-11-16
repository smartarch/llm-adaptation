The previous version could divert too many farmers from food production into spawning, leaving too little wheat to sustain the army. This version preserves a farming workforce, requests only a limited number of extra warriors, and avoids using villagers who need to eat soon for spawning. Warriors still travel to attack promptly and return before hunger disables them.

```py
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

        def assign(i, group):
            environment.assign_group(components[i], group)
            assigned.add(i)

        try:
            wheat = max(0, int(environment.farm.wheat))
        except (AttributeError, TypeError, ValueError):
            wheat = 0

        # Eat before travel or spawning when needed. Warriors eat at age 3
        # to avoid starting a Cave journey too hungry.
        for i, component in enumerate(components):
            age = self._meal_age(component)
            if age >= 5 or (
                self._role(component) == "warrior" and age >= 3
            ):
                assign(i, "eat")

        def unassigned():
            return [i for i in range(len(components)) if i not in assigned]

        # Spawn one farmer when feasible. This may briefly use all farmers,
        # but the newly spawned farmer helps restore the workforce.
        if self._farmer_spawns_requested < 1 and wheat >= 10:
            farmers = [
                i for i in unassigned()
                if self._role(components[i]) == "farmer"
                and self._meal_age(components[i]) < 5
            ]
            if len(farmers) >= 2:
                for i in farmers[:2]:
                    assign(i, "spawn farmer")
                wheat -= 10
                self._farmer_spawns_requested += 1

        # A small extra force improves kill speed without repeatedly
        # sacrificing the farming workforce. Prefer warriors for spawn work
        # when at least one farmer needs to remain available to farm.
        while self._warrior_spawns_requested < 3 and wheat >= 12:
            candidates = [
                i for i in unassigned()
                if self._meal_age(components[i]) < 3
            ]
            farmer_candidates = [
                i for i in candidates
                if self._role(components[i]) == "farmer"
            ]
            warrior_candidates = [
                i for i in candidates
                if self._role(components[i]) == "warrior"
            ]

            # Do not take the last available farmer away from the farm.
            if len(farmer_candidates) > 2:
                pair = farmer_candidates[:2]
            elif len(warrior_candidates) >= 2:
                pair = warrior_candidates[:2]
            else:
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
                # Leave at age 4 so the warrior can travel home and eat
                # before starvation makes them ineffective.
                environment.assign_group(component, "village")
            else:
                environment.assign_group(component, "attack")
```