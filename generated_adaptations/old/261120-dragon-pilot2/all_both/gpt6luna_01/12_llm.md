The assignment bug came from pre-marking warriors as eaters without charging their meals against the wheat budget. This version starts with no eat assignments, deducts wheat exactly once per meal, and only spawns from the remaining wheat while keeping a small reserve for upcoming meals. It also sends cave warriors back at hunger 3, so they can eat before risking starvation, and sends hungry warriors already in the Village to eat or farm rather than back to the Cave.

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

        # First choose non-food actions. A warrior who is due for a meal
        # stays in the Village instead of making a risky trip to the Cave.
        for component in components:
            if self._role(component) == "warrior":
                assignments[component] = (
                    "farm" if self._hunger(component) >= 3 else "cave"
                )
            else:
                assignments[component] = "farm"

        # Assign meals in urgency order, deducting exactly one wheat per meal.
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
            if wheat <= 0:
                break
            assignments[component] = "eat"
            wheat -= 1

        # Retain a modest reserve for meals that will become urgent soon,
        # without preventing the first warrior batch from being spawned.
        upcoming_meals = sum(
            1 for c in components
            if assignments[c] != "eat"
            and self._hunger(c) >= 3
        )
        meal_reserve = min(2, upcoming_meals)

        def spawn_batch(kind, cost):
            nonlocal wheat

            if kind == "warrior":
                if self._warrior_spawn_batches >= 2:
                    return False
                spawn_group = "spawn warrior"
            else:
                if self._farmer_spawn_batches >= 1:
                    return False
                spawn_group = "spawn farmer"

            if wheat - cost < meal_reserve:
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
                assignments[component] = spawn_group

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_batches += 1
            else:
                self._farmer_spawn_batches += 1
            return True

        # Create combat strength before spending wheat on the extra farmer.
        spawn_batch("warrior", 12)
        spawn_batch("warrior", 12)
        spawn_batch("farmer", 10)

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif self._hunger(component) >= 3:
                # Leaving at hunger 3 gives the warrior time to travel back
                # and eat in the Village before reaching the starvation limit.
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```