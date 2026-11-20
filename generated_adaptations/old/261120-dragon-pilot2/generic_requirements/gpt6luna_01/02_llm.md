The strategy prioritizes feeding villagers before starvation, sends healthy warriors to the Cave, and keeps farmers in the Village. It uses available pairs to request two new warriors and one new farmer, while reserving wheat for villagers who need to eat. Warriors in the Cave attack while they are fed enough to fight; those nearing starvation return to the Village to eat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Count spawn requests so the strategy does not repeatedly request
        # more than the required two warriors and one farmer.
        self._warriors_requested = 0
        self._farmers_requested = 0

    @staticmethod
    def _role(component):
        return str(component.role).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = {}
        wheat = max(0, environment.farm.wheat)

        # Eat before starvation becomes a risk. Warriors eat at 3 steps
        # without a meal so they can be sent to the Cave after eating.
        eaters = []
        for villager in components:
            threshold = 3 if self._role(villager) == "warrior" else 4
            if villager.steps_since_meal >= threshold:
                assignments[villager] = "eat"
                eaters.append(villager)

        available = [v for v in components if v not in assignments]
        reserved_wheat = len(eaters)
        remaining_wheat = max(0, wheat - reserved_wheat)

        def request_spawns(role, count, cost):
            """Assign a pair per spawn request, if workers and wheat allow."""
            nonlocal available, remaining_wheat
            requested = 0
            while requested < count and len(available) >= 2 and remaining_wheat >= cost:
                # Prefer farmers for spawn work, leaving warriors available
                # to head to the Cave.
                available.sort(key=lambda v: self._role(v) != "farmer")
                pair = available[:2]
                available = available[2:]
                for villager in pair:
                    assignments[villager] = role
                remaining_wheat -= cost
                requested += 1
            return requested

        # Fulfil the required warrior spawns first, then spawn a farmer.
        new_warriors = request_spawns(
            "spawn warrior", 2 - self._warriors_requested, 12
        )
        self._warriors_requested += new_warriors

        new_farmers = request_spawns(
            "spawn farmer", 1 - self._farmers_requested, 10
        )
        self._farmers_requested += new_farmers

        # Farmers remain in the Village; available warriors travel to the Cave.
        for villager in available:
            assignments[villager] = (
                "cave" if self._role(villager) == "warrior" else "farm"
            )

        for villager in components:
            environment.assign_group(villager, assignments[villager])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            if self._role(villager) != "warrior":
                group = "village"
            elif villager.steps_since_meal >= 4:
                # A step of travel back leaves time to eat in the Village
                # before starvation makes the warrior unable to fight.
                group = "village"
            else:
                group = "attack"

            environment.assign_group(villager, group)
```