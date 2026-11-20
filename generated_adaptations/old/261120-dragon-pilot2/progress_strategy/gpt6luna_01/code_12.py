from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        dragon_hp = environment.dragon.hp
        wheat = max(0, environment.farm.wheat)
        assignments = {}

        # Feed those closest to starvation first, preferring Warriors on ties.
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

        # Warriors who are not eating should head back to the Cave.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        if dragon_hp <= 15:
            # A late push adds damage without sacrificing the food economy
            # throughout most of the fight. Keep overdue Farmers in Village.
            for v in farmers:
                if v.steps_since_meal < 4:
                    assignments[v] = "cave"
                else:
                    assignments[v] = "farm"
        else:
            # Preserve a small meal buffer and invest surplus wheat in Warriors.
            reserve = 2
            keep_farming = 1 if len(farmers) >= 3 else 0
            spawnable = max(0, len(farmers) - keep_farming)
            pairs = min(
                spawnable // 2,
                max(0, wheat - reserve) // 12,
            )

            for v in farmers[:2 * pairs]:
                assignments[v] = "spawn warrior"
            for v in farmers[2 * pairs:]:
                assignments[v] = "farm"

        # Assign every Village component explicitly.
        for v in villagers:
            environment.assign_group(v, assignments.get(v, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp

        for v in components:
            if v.steps_since_meal >= 4:
                # Leave in time to travel home and eat before starvation.
                group = "village"
            elif v.role == "Farmer" and dragon_hp > 15:
                # Farmers normally stay home and support Warrior production.
                group = "village"
            else:
                group = "attack"

            # Assign every Cave component explicitly.
            environment.assign_group(v, group)