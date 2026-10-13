The strategy sends every Warrior in the Village to the Cave and assigns every Warrior in the Cave to attack. Farmers found in the Cave return to the Village. In the Village, two Farmers at a time are assigned to spawn groups when enough wheat is available; spawning alternates between Farmers and Warriors where possible, then remaining Farmers work on the farm. Spawn attempts are tracked so the strategy can stop after two of each type, leaving more villagers available for farming and attacking.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawn_attempts = {"spawn farmer": 0, "spawn warrior": 0}

    @staticmethod
    def _is_warrior(component):
        return str(component.role).lower() == "warrior"

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        # Warriors leave the Village as soon as possible. Farmers remain in
        # the Village, either working or helping spawn new villagers.
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)

        wheat = environment.farm.wheat
        options = []

        # Alternate spawn types when possible, preferring the type with fewer
        # successful, affordable spawn assignments so far.
        if len(farmers) >= 2:
            for group, cost in (("spawn warrior", 12), ("spawn farmer", 10)):
                if self._spawn_attempts[group] < 2 and wheat >= cost:
                    options.append((self._spawn_attempts[group], group))

        if options:
            # On a tie, prioritize Warriors to increase Dragon damage sooner.
            _, spawn_group = min(
                options,
                key=lambda item: (
                    item[0],
                    0 if item[1] == "spawn warrior" else 1,
                ),
            )
            for component in farmers[:2]:
                environment.assign_group(component, spawn_group)
            self._spawn_attempts[spawn_group] += 1
            farmers = farmers[2:]

        for component in farmers:
            environment.assign_group(component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                # Farmers are more useful producing wheat in the Village.
                environment.assign_group(component, "village")
```