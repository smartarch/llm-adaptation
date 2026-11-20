The earlier code stopped requesting warrior spawns after two attempts, even though newly spawned warriors could die before the army was large enough to kill the Dragon. This version keeps producing warriors whenever wheat and a spare pair of villagers allow it, while reserving food for villagers who need to eat. Cave warriors head back to eat before they become too hungry to fight; otherwise, they attack.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawn_requested = False

    @staticmethod
    def _is_warrior(villager):
        return str(villager.role).lower().endswith("warrior")

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = [None] * len(components)
        wheat = max(0, environment.farm.wheat)

        # Feed villagers before starvation becomes a concern. Warriors eat
        # sooner so they can return to combat without becoming too hungry.
        for i, villager in enumerate(components):
            threshold = 3 if self._is_warrior(villager) else 5
            if villager.steps_since_meal >= threshold:
                assignments[i] = "eat"

        available = [i for i, group in enumerate(assignments) if group is None]

        # Reserve wheat for villagers who need food now or soon.
        food_reserve = sum(
            1 for i, villager in enumerate(components)
            if assignments[i] == "eat" or villager.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - food_reserve)

        # Prefer farmers as spawn helpers, keeping warriors available to fight.
        farmers = [i for i in available if not self._is_warrior(components[i])]
        warriors = [i for i in available if self._is_warrior(components[i])]

        # Request a farmer once, then use additional spare pairs to grow the
        # warrior force. Do not spawn if that would leave no one to farm or
        # send to the Cave.
        spawn_group = None
        cost = 0
        if (
            not self._farmer_spawn_requested
            and len(farmers) >= 2
            and spawn_wheat >= 10
        ):
            spawn_group, cost = "spawn farmer", 10
        elif spawn_wheat >= 12 and len(available) >= 4:
            spawn_group, cost = "spawn warrior", 12

        if spawn_group is not None:
            helpers = (farmers + warriors)[:2]
            for i in helpers:
                assignments[i] = spawn_group
            if spawn_group == "spawn farmer":
                self._farmer_spawn_requested = True

        for i, villager in enumerate(components):
            if assignments[i] is None:
                assignments[i] = "cave" if self._is_warrior(villager) else "farm"

        for villager, group in zip(components, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            if not self._is_warrior(villager):
                group = "village"
            elif villager.steps_since_meal >= 3:
                # Travel back now, then eat in the Village before starvation
                # makes the warrior unable to deal damage.
                group = "village"
            else:
                group = "attack"

            environment.assign_group(villager, group)
```