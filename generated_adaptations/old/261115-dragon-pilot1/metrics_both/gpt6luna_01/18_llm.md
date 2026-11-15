The previous versions could trap Warriors in the Village by assigning them to eat whenever they were even slightly hungry, or let them reach the starvation deadline during the trip back. This version uses a simpler cycle: Warriors in the Cave return at hunger 4, eat in the Village when they reach hunger 5, then head back once fed. Only one Cave Warrior starts a return trip per call when possible, so the others keep attacking. Farmers eat before starvation; otherwise they farm or spawn villagers when wheat allows, prioritizing Warriors and preserving the requested minimum spawns.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned = {
            "spawn warrior": 0,
            "spawn farmer": 0,
        }

    @staticmethod
    def _role(component):
        return str(component.role).lower().split(".")[-1]

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, environment.farm.wheat)
        assigned = set()
        farmers = []

        # Feed Warriors that need food before traveling to the Cave. A Warrior
        # returning at hunger 5 eats now; a fed Warrior can head back.
        for component in components:
            if self._role(component) == "warrior":
                hunger = component.steps_since_meal
                if hunger >= 3:
                    self._assign(environment, component, "eat")
                    assigned.add(id(component))
                    wheat = max(0, wheat - 1)
                else:
                    self._assign(environment, component, "cave")
                    assigned.add(id(component))
            else:
                farmers.append(component)

        # Feed Farmers before they reach six consecutive steps without a meal.
        for component in farmers:
            if component.steps_since_meal >= 5 and wheat > 0:
                self._assign(environment, component, "eat")
                assigned.add(id(component))
                wheat -= 1

        # Spend wheat on one spawning pair at a time. Keep Farmers near their
        # meal deadline available to eat, and prioritize the minimum Warrior
        # spawns before the minimum Farmer spawns.
        candidates = [
            component for component in farmers
            if id(component) not in assigned
            and component.steps_since_meal < 5
        ]
        candidates.sort(
            key=lambda component: (
                component.steps_since_meal,
                -component.hp,
            )
        )

        if len(candidates) >= 2:
            if self._spawned["spawn warrior"] < 2:
                spawn_group = "spawn warrior"
                cost = 12
            elif self._spawned["spawn farmer"] < 2:
                spawn_group = "spawn farmer"
                cost = 10
            else:
                # Once the required spawns are achieved, add Warriors for damage.
                spawn_group = "spawn warrior"
                cost = 12

            if wheat >= cost:
                for component in candidates[:2]:
                    self._assign(environment, component, spawn_group)
                    assigned.add(id(component))
                self._spawned[spawn_group] += 1

        # Explicitly assign every remaining component.
        for component in components:
            if id(component) in assigned:
                continue
            if self._role(component) == "warrior":
                self._assign(environment, component, "cave")
            else:
                self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if self._role(component) == "warrior":
                warriors.append(component)
            else:
                self._assign(environment, component, "village")

        if not warriors:
            return

        # Start at most one return trip per assignment call. Return at hunger 4
        # so the Warrior reaches the Village in time to eat before starvation.
        eligible = [
            component for component in warriors
            if component.steps_since_meal >= 4
        ]
        eligible.sort(
            key=lambda component: (
                -component.steps_since_meal,
                component.hp,
            )
        )

        returning = eligible[0] if eligible else None

        for component in warriors:
            if component is returning:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```