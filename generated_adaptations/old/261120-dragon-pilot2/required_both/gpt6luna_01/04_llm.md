The failure comes from the nested `spawn` function assigning to `wheat`, which makes it local unless declared otherwise. I’ve added `nonlocal wheat` so each spawn correctly updates the available wheat balance.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0

    @staticmethod
    def _age(component):
        return getattr(component, "steps_since_meal", 0)

    @staticmethod
    def _role(component):
        return getattr(component, "role", "")

    def assign_in_village(self, components, environment, group_ids, step: int):
        decisions = {}
        wheat = max(0, getattr(environment.farm, "wheat", 0))

        # Feed villagers who are approaching the point where they need to eat.
        eaters = sorted(
            (
                c for c in components
                if (self._role(c) == "Warrior" and self._age(c) >= 3)
                or (self._role(c) != "Warrior" and self._age(c) >= 4)
            ),
            key=self._age,
            reverse=True,
        )
        for c in eaters:
            decisions[c] = "eat"
            wheat = max(0, wheat - 1)

        reserve = 2 + sum(1 for c in components if self._age(c) >= 3)

        # Prefer using Farmers for spawn groups, leaving Warriors available to
        # travel to the Cave and attack.
        candidates = [
            c for c in components
            if c not in decisions and self._age(c) < 3
        ]
        candidates.sort(key=lambda c: self._role(c) != "Farmer")

        def spawn(group, cost, remaining):
            nonlocal wheat
            spawned = 0
            while (
                remaining > 0
                and len(candidates) >= 2
                and wheat >= cost + reserve
            ):
                decisions[candidates.pop(0)] = group
                decisions[candidates.pop(0)] = group
                wheat -= cost
                remaining -= 1
                spawned += 1
            return spawned

        self._spawned_warriors += spawn(
            "spawn warrior", 12, max(0, 2 - self._spawned_warriors)
        )
        self._spawned_farmers += spawn(
            "spawn farmer", 10, max(0, 1 - self._spawned_farmers)
        )

        for c in components:
            if c in decisions:
                continue
            if self._role(c) == "Farmer":
                decisions[c] = "farm"
            elif self._age(c) >= 3:
                decisions[c] = "eat"
            else:
                decisions[c] = "cave"

        for component in components:
            environment.assign_group(component, decisions[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._role(component) != "Warrior":
                group = "village"
            elif self._age(component) >= 3:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(component, group)
```