The recent slowdown and loss appear tied to changing meal/return timing: Warriors returning at meal-age 3–4 can leave the Cave under-defended, and early meals spend wheat that could support more Warriors. I’d return to the previously reliable timing: feed Village villagers at age 5, send Cave Warriors home at age 4, and use surplus wheat for Warrior spawns while keeping a small reserve. Farmers stay home until a final push at 15 Dragon HP.

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

        # Feed villagers nearing the starvation threshold, favoring Warriors
        # on ties. Keep this timing conservative to avoid synchronized early
        # trips out of the Cave.
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

        # Warriors who are not eating return to the Cave.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        if dragon_hp <= 15:
            # Final push: healthy Farmers join the fight; hungry ones stay
            # home, where they can eat safely.
            for v in farmers:
                assignments[v] = (
                    "cave" if v.steps_since_meal < 4 else "farm"
                )
        else:
            # Spend surplus wheat on Warrior spawns while keeping a small
            # reserve for meals.
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
                group = (
                    "attack"
                    if dragon_hp <= 15 and v.steps_since_meal < 4
                    else "village"
                )
            elif v.steps_since_meal >= 4 or v.hp <= 1:
                # Return before starvation or a likely fatal counterattack.
                group = "village"
            else:
                group = "attack"

            # Explicitly assign every villager in the Cave.
            environment.assign_group(v, group)
```