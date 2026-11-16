The failures point to two issues: spawning needs to be scheduled in multiple batches, and meal trips need to be staggered so they do not leave the Dragon unattended. This version schedules up to two warrior-spawn batches and one farmer-spawn batch, prioritizes meals, and sends at most one cave warrior back to the Village per step while others can keep attacking. It explicitly reassigns every component on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_batches = 0
        self._farmer_spawn_batches = 0

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _hunger(component):
        return int(getattr(component, "steps_since_meal", 0))

    @staticmethod
    def _hp(component):
        return int(getattr(component, "hp", 1))

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        assignments = {}

        # Farmers remain in the Village. Warriors who are not due for a meal
        # head to the Cave; those who are due eat before travelling.
        for component in components:
            if self._role(component) == "warrior":
                assignments[component] = (
                    "eat" if self._hunger(component) >= 3 else "cave"
                )
            else:
                assignments[component] = "farm"

        # Feed the most urgent villagers first, keeping a small wheat reserve
        # where possible for meals needed on subsequent steps.
        eaters = [
            c for c in components
            if assignments[c] == "eat"
            or self._hunger(c) >= 5
        ]
        eaters.sort(key=lambda c: self._hunger(c), reverse=True)

        for component in eaters:
            if wheat <= 0:
                break
            assignments[component] = "eat"
            wheat -= 1

        # Each spawn batch requires two villagers assigned to its spawn group.
        # Prefer farmers, since warriors should get to the Cave to deal damage.
        def schedule_spawn(kind, cost, already_scheduled, target):
            nonlocal wheat
            if already_scheduled >= target or wheat < cost + 1:
                return False

            candidates = [
                c for c in components
                if assignments[c] == "farm"
            ]
            candidates.sort(key=lambda c: (
                self._role(c) != "farmer",
                self._hunger(c),
            ))
            if len(candidates) < 2:
                return False

            group = "spawn warrior" if kind == "warrior" else "spawn farmer"
            for component in candidates[:2]:
                assignments[component] = group

            wheat -= cost
            return True

        # Spawn warriors first for Dragon damage, then at least one farmer.
        if schedule_spawn(
            "warrior", 12, self._warrior_spawn_batches, 2
        ):
            self._warrior_spawn_batches += 1

        if schedule_spawn(
            "farmer", 10, self._farmer_spawn_batches, 1
        ):
            self._farmer_spawn_batches += 1

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            c for c in components
            if self._role(c) == "warrior" and self._hp(c) > 0
        ]

        # Return at most one warrior per step for a meal. This staggers
        # journeys so that other warriors can keep attacking.
        due_to_return = sorted(
            (c for c in warriors if self._hunger(c) >= 4),
            key=self._hunger,
            reverse=True,
        )
        returning = due_to_return[:1]
        returning_ids = {id(c) for c in returning}

        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif id(component) in returning_ids:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```