from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_cave_count = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, environment.farm.wheat)
        assignments = {}

        # Eat before starvation, prioritizing Warriors when villagers are
        # equally overdue. Meals are accounted for before considering spawns.
        meal_order = sorted(
            villagers,
            key=lambda v: (
                -v.steps_since_meal,
                0 if v.role == "Warrior" else 1,
            ),
        )
        for v in meal_order:
            if v.steps_since_meal >= 5 and wheat >= 1:
                assignments[v] = "eat"
                wheat -= 1

        # Fed Warriors return to the Cave; Warriors who need a meal remain
        # assigned to "eat" above.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        # Keep a small wheat buffer for meals. Leave at least one Farmer
        # farming once there is a larger workforce; otherwise use available
        # pairs to spawn Warriors.
        reserve = 2
        keep_farming = 1 if len(farmers) >= 3 else 0
        candidates = max(0, len(farmers) - keep_farming)
        pairs = min(
            candidates // 2,
            max(0, wheat - reserve) // 12,
        )

        for v in farmers[:2 * pairs]:
            assignments[v] = "spawn warrior"

        for v in farmers[2 * pairs:]:
            assignments[v] = "farm"

        # Explicitly assign every villager on every call.
        for v in villagers:
            environment.assign_group(v, assignments.get(v, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        self._last_cave_count = len(villagers)

        for v in villagers:
            if v.role == "Farmer":
                # Keep the food supply in the Village; Farmers are not sent
                # into the Cave where they cannot eat or produce wheat.
                group = "village"
            elif v.hp <= 1 or v.steps_since_meal >= 4:
                # Return early enough to travel home and eat safely.
                group = "village"
            else:
                group = "attack"

            # Explicitly assign every villager on every call.
            environment.assign_group(v, group)