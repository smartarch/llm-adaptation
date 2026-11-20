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

        # Feed before spending wheat on recruitment. The age threshold leaves
        # time for villagers to eat before reaching the starvation limit.
        hungry = sorted(
            (c for c in components if self._age(c) >= 4),
            key=self._age,
            reverse=True,
        )
        for c in hungry:
            decisions[c] = "eat"
            if wheat > 0:
                wheat -= 1

        # Spawn only with recently fed villagers, leaving older villagers
        # available to eat or continue farming.
        candidates = [
            c for c in components
            if c not in decisions and self._age(c) <= 1
        ]
        candidates.sort(key=lambda c: self._role(c) != "Farmer")

        def spawn(group, cost, target_count, already_spawned):
            nonlocal wheat
            spawned = 0
            while (
                already_spawned + spawned < target_count
                and len(candidates) >= 2
                and wheat >= cost + 2
            ):
                first = candidates.pop(0)
                second = candidates.pop(0)
                decisions[first] = group
                decisions[second] = group
                wheat -= cost
                spawned += 1
            return spawned

        # Recruit Warriors first to build enough damage to kill the Dragon.
        self._warrior_spawn_orders += spawn(
            "spawn warrior", 12, 3, self._warrior_spawn_orders
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
                # Feed Warriors before sending them on the Village-to-Cave trip.
                decisions[c] = "eat"
            else:
                decisions[c] = "cave"

        for component in components:
            environment.assign_group(component, decisions[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if self._role(c) == "Warrior"]

        # Alternate return thresholds to avoid making the entire attack force
        # leave the Cave on the same step. Returning at age 3 or 4 gives time
        # to reach the Village and eat before starvation.
        return_early = set(id(c) for i, c in enumerate(warriors) if i % 2 == 0)

        for component in components:
            if self._role(component) != "Warrior":
                group = "village"
            elif self._age(component) >= 5:
                group = "village"
            elif self._age(component) >= 3 and id(component) in return_early:
                group = "village"
            elif self._age(component) >= 4:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(component, group)