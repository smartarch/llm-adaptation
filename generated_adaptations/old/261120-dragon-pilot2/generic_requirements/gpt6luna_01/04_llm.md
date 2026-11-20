The previous strategy requested two warrior spawns at once, which could tie up too many villagers and delay farming or combat. This version requests one spawn at a time, prioritizes warriors, reserves wheat for meals, and sends cave warriors back early enough to eat before starvation. It also assigns every villager on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _role(villager):
        return str(villager.role).lower()

    @classmethod
    def _is_warrior(cls, villager):
        return cls._role(villager).endswith("warrior")

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = [None] * len(components)
        wheat = max(0, environment.farm.wheat)

        # Eat when close to the starvation limit. Warriors are sent to eat
        # sooner than farmers so they can return to combat safely.
        eaters = []
        for i, villager in enumerate(components):
            threshold = 3 if self._is_warrior(villager) else 5
            if villager.steps_since_meal >= threshold:
                assigned[i] = "eat"
                eaters.append(i)

        available = [i for i, group in enumerate(assigned) if group is None]

        # Keep enough wheat for villagers who need food now or imminently.
        reserve = len(eaters) + sum(
            1 for i in available if components[i].steps_since_meal >= 4
        )
        wheat_for_spawning = max(0, wheat - reserve)

        # Request at most one spawn per turn. Use farmers as helpers first,
        # preserving warriors for combat whenever possible.
        spawn_group = None
        spawn_cost = 0
        if self._warrior_spawn_requests < 2:
            spawn_group, spawn_cost = "spawn warrior", 12
        elif self._farmer_spawn_requests < 1:
            spawn_group, spawn_cost = "spawn farmer", 10

        if spawn_group is not None and wheat_for_spawning >= spawn_cost and len(available) >= 2:
            farmers = [i for i in available if not self._is_warrior(components[i])]
            warriors = [i for i in available if self._is_warrior(components[i])]
            helpers = (farmers + warriors)[:2]

            for i in helpers:
                assigned[i] = spawn_group

            if spawn_group == "spawn warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

        # Farmers work in the Village; warriors head to the Cave.
        for i, villager in enumerate(components):
            if assigned[i] is None:
                assigned[i] = "cave" if self._is_warrior(villager) else "farm"

        for villager, group in zip(components, assigned):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            if not self._is_warrior(villager):
                group = "village"
            elif villager.steps_since_meal >= 4:
                # Allow a step to travel back before the villager must eat.
                group = "village"
            else:
                group = "attack"

            environment.assign_group(villager, group)
```