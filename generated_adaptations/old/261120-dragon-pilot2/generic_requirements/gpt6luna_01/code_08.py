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

        # Eat in the Village before hunger becomes disabling. Keep warriors'
        # meals timely so they can return to fighting promptly.
        for i, villager in enumerate(components):
            threshold = 4 if self._is_warrior(villager) else 5
            if villager.steps_since_meal >= threshold:
                assignments[i] = "eat"

        available = [i for i, group in enumerate(assignments) if group is None]

        # Reserve food for villagers who will need it soon.
        food_reserve = sum(
            1
            for i, villager in enumerate(components)
            if assignments[i] == "eat" or villager.steps_since_meal >= 4
        )
        spawn_wheat = max(0, wheat - food_reserve)

        farmers = [i for i in available if not self._is_warrior(components[i])]
        warriors = [i for i in available if self._is_warrior(components[i])]

        # Keep one farmer working whenever possible. This sustains food
        # production while the remaining villagers can help with spawning.
        keep_farming = farmers[0] if farmers else None
        helpers = [i for i in available if i != keep_farming]

        spawn_group = None
        cost = 0

        # Secure the requested extra farmer, then continue building the
        # warrior force when spare helpers and wheat are available.
        if (
            not self._farmer_spawn_requested
            and len(helpers) >= 2
            and spawn_wheat >= 10
        ):
            spawn_group, cost = "spawn farmer", 10
        elif len(helpers) >= 2 and spawn_wheat >= 12:
            spawn_group, cost = "spawn warrior", 12

        if spawn_group is not None:
            # Prefer farmers as spawn helpers, but retain the designated
            # farmer who is keeping the farm running.
            helper_farmers = [i for i in helpers if not self._is_warrior(components[i])]
            helper_warriors = [i for i in helpers if self._is_warrior(components[i])]
            pair = (helper_farmers + helper_warriors)[:2]

            if len(pair) == 2:
                for i in pair:
                    assignments[i] = spawn_group
                if spawn_group == "spawn farmer":
                    self._farmer_spawn_requested = True
                else:
                    self._warrior_spawn_requests += 1

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
                # Return with time to travel back and eat before starvation.
                group = "village"
            else:
                group = "attack"

            environment.assign_group(villager, group)