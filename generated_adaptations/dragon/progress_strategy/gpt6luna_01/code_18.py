from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        dragon_hp = environment.dragon.hp
        wheat = max(0, environment.farm.wheat)
        assignments = {}

        # Feed villagers close to starvation first, giving Warriors priority
        # on ties. Leave the proven Warrior travel timing unchanged.
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

        # Warriors not eating should return to the Cave.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        if dragon_hp <= 30:
            # Add Farmer damage during the final phase, but keep Farmers
            # needing food in the Village.
            for v in farmers:
                assignments[v] = (
                    "cave" if v.steps_since_meal < 4 else "farm"
                )
        else:
            # Spend surplus wheat on Warrior spawns while retaining a small
            # reserve for food.
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

        # Explicitly assign every villager in the Village.
        for v in villagers:
            environment.assign_group(v, assignments.get(v, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp

        for v in components:
            if v.role == "Farmer":
                if dragon_hp <= 30 and v.steps_since_meal < 4:
                    group = "attack"
                else:
                    group = "village"
            elif v.steps_since_meal >= 4 or v.hp <= 1:
                # Return before starvation or a likely fatal counterattack.
                group = "village"
            else:
                group = "attack"

            # Explicitly assign every villager in the Cave.
            environment.assign_group(v, group)