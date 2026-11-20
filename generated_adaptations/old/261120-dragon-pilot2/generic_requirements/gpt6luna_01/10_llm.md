To shorten the fight, this version prioritizes the two required warrior spawns before requesting a farmer, then continues recruiting warriors when there are spare villagers and wheat. It still reserves wheat for meals and sends cave warriors back in time to eat before starvation makes them unable to attack.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requested = False

    @staticmethod
    def _is_warrior(villager):
        return str(villager.role).lower().endswith("warrior")

    def assign_in_village(self, components, environment, group_ids, step: int):
        assignments = [None] * len(components)
        wheat = max(0, environment.farm.wheat)

        # Feed villagers before starvation makes them ineffective.
        for i, villager in enumerate(components):
            threshold = 4 if self._is_warrior(villager) else 5
            if villager.steps_since_meal >= threshold:
                assignments[i] = "eat"

        available = [i for i, group in enumerate(assignments) if group is None]

        # Preserve food for villagers who need a meal now or soon.
        food_reserve = sum(
            1
            for i, villager in enumerate(components)
            if assignments[i] == "eat" or villager.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - food_reserve)

        # When wheat is low, keep a farmer working. With a larger reserve,
        # use all available villagers to recruit without delaying combat.
        keep_farming = None
        if wheat < 20:
            farm_workers = [
                i for i in available if not self._is_warrior(components[i])
            ]
            if farm_workers:
                keep_farming = farm_workers[0]

        helpers = [i for i in available if i != keep_farming]
        helper_farmers = [
            i for i in helpers if not self._is_warrior(components[i])
        ]
        helper_warriors = [
            i for i in helpers if self._is_warrior(components[i])
        ]

        # Secure the required warrior recruits first, then the required
        # farmer. After that, use remaining spare pairs to recruit warriors.
        if self._warrior_spawn_requests < 2:
            spawn_group, cost = "spawn warrior", 12
        elif not self._farmer_spawn_requested:
            spawn_group, cost = "spawn farmer", 10
        else:
            spawn_group, cost = "spawn warrior", 12

        if len(helpers) >= 2 and spawn_wheat >= cost:
            pair = (helper_farmers + helper_warriors)[:2]
            if len(pair) == 2:
                for i in pair:
                    assignments[i] = spawn_group
                if spawn_group == "spawn warrior":
                    self._warrior_spawn_requests += 1
                else:
                    self._farmer_spawn_requested = True

        # Farmers work the farm; warriors travel to the Cave to fight.
        for i, villager in enumerate(components):
            if assignments[i] is None:
                assignments[i] = "cave" if self._is_warrior(villager) else "farm"

        for villager, group in zip(components, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            if not self._is_warrior(villager):
                group = "village"
            elif villager.steps_since_meal >= 4:
                # Return in time to travel to the Village and eat safely.
                group = "village"
            else:
                group = "attack"

            environment.assign_group(villager, group)
```