The remaining failure is likely a narrow timing/damage miss. This version makes recruitment more aggressive and reduces the number of Warriors leaving the Cave early, while still sending them back before starvation becomes imminent. It prioritizes feeding villagers in the Village and keeps a small wheat reserve rather than withholding wheat needed for recruitment.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_orders = 0
        self._farmer_spawn_orders = 0

    @staticmethod
    def _role(component):
        return getattr(component, "role", "")

    @staticmethod
    def _age(component):
        return max(0, getattr(component, "steps_since_meal", 0))

    def assign_in_village(self, components, environment, group_ids, step: int):
        decisions = {}
        wheat = max(0, getattr(environment.farm, "wheat", 0))

        # Feed villagers before using wheat for recruitment. A Warrior leaves
        # after eating, so avoid sending one to the Cave while already hungry.
        hungry = sorted(
            (
                c for c in components
                if self._age(c) >= (
                    3 if self._role(c) == "Warrior" else 4
                )
            ),
            key=self._age,
            reverse=True,
        )
        for c in hungry:
            decisions[c] = "eat"
            wheat = max(0, wheat - 1)

        # Keep only a small meal reserve so recruitment is not delayed
        # unnecessarily.
        reserve = min(2, sum(1 for c in components if self._age(c) >= 2))
        candidates = [
            c for c in components
            if c not in decisions and self._age(c) <= 2
        ]
        candidates.sort(key=lambda c: self._role(c) != "Farmer")

        def spawn(group, cost, target, already_spawned):
            nonlocal wheat
            count = 0
            while (
                already_spawned + count < target
                and len(candidates) >= 2
                and wheat >= cost + reserve
            ):
                first = candidates.pop(0)
                second = candidates.pop(0)
                decisions[first] = group
                decisions[second] = group
                wheat -= cost
                count += 1
            return count

        # Recruit a large force early; use available Farmers for spawn groups
        # before assigning Warriors away from the attack.
        self._warrior_spawn_orders += spawn(
            "spawn warrior", 12, 20, self._warrior_spawn_orders
        )
        self._farmer_spawn_orders += spawn(
            "spawn farmer", 10, 1, self._farmer_spawn_orders
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
        warriors = [c for c in components if self._role(c) == "Warrior"]

        # Stagger only a small fraction of meal trips at age 3. The rest keep
        # attacking until age 4, then return to the Village to eat.
        early_return_ids = {
            id(c) for index, c in enumerate(warriors)
            if index % 6 == 0
        }

        for component in components:
            if self._role(component) != "Warrior":
                group = "village"
            elif self._age(component) >= 4:
                group = "village"
            elif self._age(component) >= 3 and id(component) in early_return_ids:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(component, group)
```