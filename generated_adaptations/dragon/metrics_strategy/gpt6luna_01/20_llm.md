I’d simplify spawning to one pair for each requested type, rather than treating two spawn requests as two villagers. The schedule also prioritizes eating over spawning and sends Cave Warriors back before their hunger reaches the starvation threshold. If Warriors’ hunger is staggered, some can keep attacking while others travel back for food.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_pair_assigned = False
        self._farmer_pair_assigned = False

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        meals_needed = 0
        available_farmers = []

        for component in components:
            if component.role == "Warrior":
                # Eat if this Warrior has missed a meal; otherwise return to
                # the Cave promptly.
                if component.steps_since_meal > 0:
                    self._assign(environment, component, "eat")
                    meals_needed += 1
                else:
                    self._assign(environment, component, "cave")
            elif component.steps_since_meal >= 5:
                self._assign(environment, component, "eat")
                meals_needed += 1
            else:
                available_farmers.append(component)

        wheat = environment.farm.wheat

        # Use a pair to spawn one Warrior first, then one Farmer, when meals
        # and a small food reserve can still be covered.
        plans = []
        if not self._warrior_pair_assigned:
            plans.append(("spawn warrior", 12, "warrior"))
        if not self._farmer_pair_assigned:
            plans.append(("spawn farmer", 10, "farmer"))

        for group, cost, role in plans:
            if len(available_farmers) < 2:
                continue
            if wheat < cost + meals_needed + 1:
                continue

            pair = available_farmers[:2]
            available_farmers = available_farmers[2:]
            for component in pair:
                self._assign(environment, component, group)

            wheat -= cost
            if role == "warrior":
                self._warrior_pair_assigned = True
            else:
                self._farmer_pair_assigned = True

        for component in available_farmers:
            self._assign(environment, component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if component.role == "Warrior":
                warriors.append(component)
            else:
                self._assign(environment, component, "village")

        # A return trip takes a step, so do not wait until starvation begins.
        # At hunger 3, stagger a return where possible; at hunger 4+, return
        # everyone who needs food.
        urgent = [
            component for component in warriors
            if component.steps_since_meal >= 4
        ]

        if urgent:
            returning = urgent
        else:
            candidates = [
                component for component in warriors
                if component.steps_since_meal >= 3
            ]
            returning = candidates[:1]

        for component in warriors:
            if any(component is returning_component for returning_component in returning):
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")
```