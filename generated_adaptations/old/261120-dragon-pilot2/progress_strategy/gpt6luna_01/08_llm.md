The previous policy was conservative about spending wheat and waited until late to add Farmers to the attack. This version uses a smaller, urgency-based food reserve so surplus wheat can produce Warriors sooner, then sends one Farmer to fight once the Dragon is weakened and the rest at the final push. Warriors still return to eat before starvation, and every villager is explicitly reassigned on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_cave_count = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        dragon_hp = environment.dragon.hp
        wheat = max(0, environment.farm.wheat)
        self._last_cave_count = getattr(self, "_last_cave_count", 0)

        assignments = {}

        # Feed villagers close to starvation first. Warriors win ties because
        # their attacks are the main source of damage.
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

        # Send fed Warriors back to the Cave promptly.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        if dragon_hp <= 35:
            # Stop investing in the economy and send all available Farmers
            # toward the fight.
            for v in farmers:
                assignments[v] = "cave"
        else:
            if dragon_hp <= 55 and farmers:
                # Add early damage while retaining a Farmer to produce food.
                assignments[farmers.pop()] = "cave"

            population = len(villagers) + self._last_cave_count
            urgent_meals = sum(
                1 for v in villagers
                if v not in assignments and v.steps_since_meal >= 4
            )
            reserve = max(2, urgent_meals + 1)

            # Keep one Farmer working when possible. Spend only wheat above a
            # small reserve, prioritizing Warrior spawns.
            keep_farming = 1 if len(farmers) >= 3 else 0
            spawnable_farmers = max(0, len(farmers) - keep_farming)
            pairs = min(
                spawnable_farmers // 2,
                max(0, wheat - reserve) // 12,
            )

            for v in farmers[:2 * pairs]:
                assignments[v] = "spawn warrior"

            for v in farmers[2 * pairs:]:
                assignments[v] = "farm"

        for v in villagers:
            if v not in assignments:
                assignments[v] = "farm"
            environment.assign_group(v, assignments[v])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        self._last_cave_count = len(villagers)
        dragon_hp = environment.dragon.hp

        for v in villagers:
            if v.role == "Farmer":
                group = "attack" if dragon_hp <= 55 else "village"
            elif v.steps_since_meal >= 4:
                # Leave in time to travel back and eat before starvation.
                group = "village"
            else:
                group = "attack"

            environment.assign_group(v, group)
```