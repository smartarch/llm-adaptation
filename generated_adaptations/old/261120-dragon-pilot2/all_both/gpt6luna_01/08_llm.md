The meal rotation must prioritize safety over keeping every warrior in the Cave: any Cave warrior nearing meal time returns, rather than limiting returns to one per step. In the Village, meals are allocated before spawning, and spawning only uses wheat left after those meals. Healthy warriors are sent to attack, while warriors that need food stay in the Village or work the farm until they can eat.

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

        for component in components:
            role = self._role(component)
            hunger = self._hunger(component)

            if role == "warrior":
                # Eat before returning to the Cave; otherwise travel and
                # another attack can put a warrior dangerously close to starving.
                assignments[component] = "eat" if hunger >= 3 else "cave"
            else:
                assignments[component] = "farm"

        # Farmers can wait longer between meals than warriors, who travel
        # between the Cave and Village. Feed the most urgent villagers first.
        meal_candidates = [
            c for c in components
            if self._hunger(c) >= (
                3 if self._role(c) == "warrior" else 5
            )
        ]
        meal_candidates.sort(
            key=lambda c: (
                self._hunger(c),
                self._role(c) == "warrior",
            ),
            reverse=True,
        )

        for component in meal_candidates:
            if wheat == 0:
                break
            assignments[component] = "eat"
            wheat -= 1

        # Preserve a little wheat for villagers approaching meal time. When
        # villagers are well-fed, this reserve is zero so initial wheat can
        # fund the first warrior spawn.
        imminent_meals = sum(
            1 for c in components
            if assignments[c] != "eat"
            and self._hunger(c) >= 2
        )
        reserve = min(4, imminent_meals)

        def spawn_batch(kind, cost):
            nonlocal wheat

            if kind == "warrior":
                if self._warrior_spawn_batches >= 2:
                    return False
                group = "spawn warrior"
            else:
                if self._farmer_spawn_batches >= 1:
                    return False
                group = "spawn farmer"

            if wheat < cost + reserve:
                return False

            candidates = [
                c for c in components
                if assignments[c] in ("farm", "cave")
            ]
            candidates.sort(
                key=lambda c: (
                    self._role(c) != "farmer",
                    self._hunger(c),
                )
            )
            if len(candidates) < 2:
                return False

            for component in candidates[:2]:
                assignments[component] = group

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_batches += 1
            else:
                self._farmer_spawn_batches += 1
            return True

        # Spawn warriors first to increase Dragon damage, then a farmer when
        # food and available workers allow it.
        spawn_batch("warrior", 12)
        spawn_batch("farmer", 10)

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif self._hunger(component) >= 3:
                # Return early enough to allow for the travel step and a meal
                # in the Village before starvation becomes possible.
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```