The main change is to stagger Warrior meal trips: send at most one hungry Warrior back per turn when possible, while keeping the others attacking. Warriors that are already at the starvation threshold return immediately. In the Village, Warriors eat before heading back to the Cave, and Farmers eat before they risk starvation. Spawning is limited to the requested first two of each type and only uses wheat beyond a reserve for meals.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0

    @staticmethod
    def _assign(environment, component, group, group_ids):
        if group not in group_ids:
            raise ValueError(f"Required group {group!r} is not available")
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers_available = []
        meals_due = 0

        for component in components:
            if component.role == "Farrior":  # handled below for compatibility
                pass

            if component.role == "Warrior":
                # Returning Warriors should eat before making the trip back.
                if component.steps_since_meal >= 4:
                    self._assign(environment, component, "eat", group_ids)
                    meals_due += 1
                else:
                    self._assign(environment, component, "cave", group_ids)
            else:
                # Farmers remain in the Village and eat before starvation.
                if component.steps_since_meal >= 5:
                    self._assign(environment, component, "eat", group_ids)
                    meals_due += 1
                else:
                    farmers_available.append(component)

        # Keep wheat available for meals rather than spending the whole stock
        # on spawning. Spawn in pairs, prioritizing Warriors.
        wheat_for_spawning = max(0, environment.farm.wheat - meals_due - 2)
        plans = []
        if self._spawned_warriors < 2:
            plans.append(("spawn warrior", 12, "warrior"))
        if self._spawned_farmers < 2:
            plans.append(("spawn farmer", 10, "farmer"))

        for group, cost, kind in plans:
            if len(farmers_available) < 2 or wheat_for_spawning < cost:
                continue

            pair = farmers_available[:2]
            farmers_available = farmers_available[2:]
            for component in pair:
                self._assign(environment, component, group, group_ids)

            wheat_for_spawning -= cost
            if kind == "warrior":
                self._spawned_warriors += 1
            else:
                self._spawned_farmers += 1

        for component in farmers_available:
            self._assign(environment, component, "farm", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Farmers should not be in the Cave; send them back to work.
        for component in farmers:
            self._assign(environment, component, "village", group_ids)

        # Anyone at five or more steps without food needs to head back.
        # Otherwise, stagger returns by sending at most one Warrior back
        # when they reach four steps without a meal.
        urgent = [c for c in warriors if c.steps_since_meal >= 5]
        for component in urgent:
            self._assign(environment, component, "village", group_ids)

        candidates = [
            c for c in warriors
            if c.steps_since_meal >= 4 and c.steps_since_meal < 5
        ]
        return_one = max(candidates, key=lambda c: c.steps_since_meal) if candidates else None

        for component in warriors:
            if component in urgent:
                continue
            if component is return_one:
                self._assign(environment, component, "village", group_ids)
            else:
                self._assign(environment, component, "attack", group_ids)
```