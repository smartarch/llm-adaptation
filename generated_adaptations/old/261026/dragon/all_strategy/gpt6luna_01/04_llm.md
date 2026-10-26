The earlier strategy stopped spawning Warriors after two attempts, so it could not replace losses. This version keeps Warrior spawning available whenever the Village has enough wheat and at least two Farmers. It also attempts up to two Farmer spawns when there is a larger wheat reserve, leaving the rest of the workforce farming.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawn_attempts = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)

        wheat = environment.farm.wheat
        remaining = list(farmers)

        # Use surplus wheat to build up the farming workforce, but limit these
        # attempts so that Warrior production remains the priority.
        if (
            self._farmer_spawn_attempts < 2
            and wheat >= 22
            and len(remaining) >= 2
        ):
            for component in remaining[:2]:
                environment.assign_group(component, "spawn farmer")
            del remaining[:2]
            wheat -= 10
            self._farmer_spawn_attempts += 1

        # Keep this decision dynamic: Warriors may be lost in the Cave, so
        # continue spawning replacements whenever resources allow.
        if wheat >= 12 and len(remaining) >= 2:
            for component in remaining[:2]:
                environment.assign_group(component, "spawn warrior")
            del remaining[:2]

        for component in remaining:
            environment.assign_group(component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")
```