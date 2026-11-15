I’d focus on getting multiple Warriors into the Cave early, then keep meal trips staggered so other Warriors can continue attacking. A Warrior leaves the Cave at three steps without food, giving them time to travel and eat before starvation; urgent return trips take priority. Farmers eat before starvation, and spawn assignments are made only when a pair and enough wheat are available.

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
        available_farmers = []
        meals_assigned = 0

        for component in components:
            if component.role == "Warrior":
                # Feed returning Warriors promptly; otherwise send them back
                # to keep pressure on the Dragon.
                if component.steps_since_meal >= 3:
                    self._assign(environment, component, "eat")
                    meals_assigned += 1
                else:
                    self._assign(environment, component, "cave")
            elif component.steps_since_meal >= 5:
                self._assign(environment, component, "eat")
                meals_assigned += 1
            else:
                available_farmers.append(component)

        # Prioritize Warrior spawns, while preserving wheat for meals.
        wheat = max(0, environment.farm.wheat - meals_assigned - 2)
        spawn_plans = []

        if self._warrior_spawn_requests < 2:
            spawn_plans.append(("spawn warrior", 12, "warrior"))
        if self._farmer_spawn_requests < 2:
            spawn_plans.append(("spawn farmer", 10, "farmer"))

        for group, cost, kind in spawn_plans:
            if len(available_farmers) < 2 or wheat < cost:
                continue

            pair = available_farmers[:2]
            available_farmers = available_farmers[2:]
            for farmer in pair:
                self._assign(environment, farmer, group)

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

        for farmer in available_farmers:
            self._assign(environment, farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if component.role == "Warrior":
                warriors.append(component)
            else:
                self._assign(environment, component, "village")

        # Return the hungriest Warrior first to stagger trips. At five steps
        # without food, return every Warrior at that urgent threshold.
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
            returning = []
            if candidates:
                returning = [
                    max(candidates, key=lambda c: c.steps_since_meal)
                ]

        for component in warriors:
            if any(component is returning_component
                   for returning_component in returning):
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```