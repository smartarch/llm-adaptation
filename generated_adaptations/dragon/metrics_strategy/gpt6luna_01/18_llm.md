I’d make meal timing depend on the villager’s current location: a Warrior returning to the Village eats as soon as it has missed a meal, then heads back to the Cave. In the Cave, returns are staggered when possible, but Warriors do not wait until starvation is imminent. Farmers eat before the six-step starvation threshold; available pairs can spawn the requested Warriors and Farmers while keeping a wheat reserve for meals.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        meals_assigned = 0

        for component in components:
            if component.role == "Warrior":
                # Eat on arrival if this Warrior has gone without a meal.
                if component.steps_since_meal > 0:
                    self._assign(environment, component, "eat")
                    meals_assigned += 1
                else:
                    self._assign(environment, component, "cave")
            elif component.steps_since_meal >= 5:
                self._assign(environment, component, "eat")
                meals_assigned += 1
            else:
                farmers.append(component)

        # Do not spend wheat needed for meals. Spawn requests use pairs.
        wheat = max(0, environment.farm.wheat - meals_assigned - 1)

        plans = []
        if self._farmer_spawn_requests < 2:
            plans.append(("spawn farmer", 10, "farmer"))
        if self._warrior_spawn_requests < 2:
            plans.append(("spawn warrior", 12, "warrior"))

        for group, cost, kind in plans:
            if len(farmers) < 2 or wheat < cost:
                continue

            pair = farmers[:2]
            farmers = farmers[2:]
            for component in pair:
                self._assign(environment, component, group)

            wheat -= cost
            if kind == "farmer":
                self._farmer_spawn_requests += 1
            else:
                self._warrior_spawn_requests += 1

        for component in farmers:
            self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if component.role == "Warrior":
                warriors.append(component)
            else:
                self._assign(environment, component, "village")

        # Hunger 5 is urgent. Otherwise stagger trips, sending at most one
        # Warrior back at hunger 3 or more while other Warriors can attack.
        urgent = [
            component for component in warriors
            if component.steps_since_meal >= 5
        ]

        if urgent:
            returning = urgent
        else:
            candidates = [
                component for component in warriors
                if component.steps_since_meal >= 3
            ]
            if len(warriors) <= 1:
                candidates = [
                    component for component in warriors
                    if component.steps_since_meal >= 4
                ]

            returning = []
            if candidates:
                returning = [
                    max(candidates, key=lambda c: c.steps_since_meal)
                ]

        for component in warriors:
            if any(component is item for item in returning):
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```