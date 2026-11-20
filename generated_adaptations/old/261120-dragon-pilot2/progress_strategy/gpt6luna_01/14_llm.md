The biggest avoidable delay in the successful runs is that Warriors sometimes return to the Village together, leaving the Cave empty and allowing the Dragon to regenerate. This version staggers their return: some head home at meal-age 3, while the rest return by age 4, so there should still be Warriors attacking while others travel to eat. Farmers stay in the Village to sustain Warrior spawns, joining the fight only when the Dragon is nearly defeated.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        dragon_hp = environment.dragon.hp
        wheat = max(0, environment.farm.wheat)
        assignments = {}

        # Feed villagers before starvation becomes a risk, prioritizing
        # Warriors on ties.
        meal_order = sorted(
            villagers,
            key=lambda v: (
                -v.steps_since_meal,
                0 if v.role == "Warrior" else 1,
            ),
        )
        for v in meal_order:
            if v.steps_since_meal >= 4 and wheat >= 1:
                assignments[v] = "eat"
                wheat -= 1

        # Send Warriors that are not eating back to the Cave.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        if dragon_hp <= 15:
            # Stop spending effort on new recruits and bring healthy Farmers
            # to the fight. Farmers needing food remain in the Village.
            for v in farmers:
                assignments[v] = (
                    "cave" if v.steps_since_meal < 4 else "farm"
                )
        else:
            # Preserve a minimal food buffer and spawn Warriors from surplus.
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
        warriors = [v for v in components if v.role == "Warrior"]
        warrior_index = {id(v): i for i, v in enumerate(warriors)}

        for v in components:
            if v.role == "Farmer":
                group = (
                    "attack"
                    if dragon_hp <= 15 and v.steps_since_meal < 4
                    else "village"
                )
            else:
                age = v.steps_since_meal
                index = warrior_index[id(v)]

                # Alternate early returns at age 3; everyone else heads home
                # by age 4, leaving a staggered stream of attackers.
                should_return = (
                    v.hp <= 1
                    or age >= 4
                    or (age >= 3 and index % 2 == 0)
                )
                group = "village" if should_return else "attack"

            # Explicitly assign every villager in the Cave.
            environment.assign_group(v, group)
```