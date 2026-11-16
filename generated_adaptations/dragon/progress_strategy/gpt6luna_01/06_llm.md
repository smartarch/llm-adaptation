The earlier policy waited until the Dragon had only 12 HP before sending Farmers to help. This version starts a staged final push at 30 HP: one Farmer joins the attack while another can keep producing food, then all available Farmers join at 12 HP. Before then, it prioritizes Warrior spawns while preserving a small wheat reserve, and keeps the proven conservative Warrior meal-return timing.

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
        population = len(villagers) + self._last_cave_count

        assignments = {}

        # Feed overdue villagers first. A Warrior meal helps preserve the
        # Dragon damage output; a Farmer meal preserves food production.
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

        # Warriors in the Village should head back as soon as they have eaten.
        for v in villagers:
            if v.role == "Warrior" and v not in assignments:
                assignments[v] = "cave"

        farmers = [
            v for v in villagers
            if v.role == "Farmer" and v not in assignments
        ]

        if dragon_hp <= 12:
            # Full final push: the remaining Farmers add damage immediately
            # after travelling to the Cave.
            for v in farmers:
                assignments[v] = "cave"
        else:
            # Start sending a Farmer to help before the Dragon is nearly dead,
            # but retain one Farmer for food production until the final push.
            if dragon_hp <= 30 and farmers:
                assignments[farmers.pop()] = "cave"

            # Keep a reserve for upcoming meals. Spend surplus wheat on
            # Warriors, since they deal substantially more damage than Farmers.
            reserve = max(5, population // 2)
            usable_farmers = max(0, len(farmers) - 1) if len(farmers) >= 3 else len(farmers)
            pairs = min(
                usable_farmers // 2,
                max(0, wheat - reserve) // 12,
            )

            for v in farmers[:2 * pairs]:
                assignments[v] = "spawn warrior"

            for v in farmers[2 * pairs:]:
                assignments[v] = "farm"

        # Explicitly assign every Village component on every call.
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
                group = "attack" if dragon_hp <= 30 else "village"
            elif v.steps_since_meal >= 4:
                # Allow time to travel home and eat before starvation.
                group = "village"
            else:
                group = "attack"

            # Explicitly assign every Cave component on every call.
            environment.assign_group(v, group)
```