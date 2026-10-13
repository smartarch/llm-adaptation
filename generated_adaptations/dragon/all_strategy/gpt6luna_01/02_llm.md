The strategy sends every Warrior to the Cave and has every Warrior there attack immediately; Farmers in the Cave return to the Village. In the Village, it uses available wheat and pairs of Farmers to make up to two spawn assignments for each type, prioritizing Warriors, while keeping Farmers on the farm when they are not spawning. Every component is explicitly assigned on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawn_attempts = 0
        self._warrior_spawn_attempts = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        # Warriors leave the Village to fight; Farmers can farm or spawn.
        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)

        available = list(farmers)
        wheat = environment.farm.wheat

        # Use pairs of Farmers to spawn Warriors first, since they accelerate
        # damage against the Dragon.
        if (
            self._warrior_spawn_attempts < 2
            and wheat >= 12
            and len(available) >= 2
        ):
            for component in available[:2]:
                environment.assign_group(component, "spawn warrior")
            del available[:2]
            wheat -= 12
            self._warrior_spawn_attempts += 1

        # Spawn Farmers as well, to sustain the workforce and wheat supply.
        if (
            self._farmer_spawn_attempts < 2
            and wheat >= 10
            and len(available) >= 2
        ):
            for component in available[:2]:
                environment.assign_group(component, "spawn farmer")
            del available[:2]
            wheat -= 10
            self._farmer_spawn_attempts += 1

        # Explicitly keep all remaining Farmers working on the farm.
        for component in available:
            environment.assign_group(component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")
```