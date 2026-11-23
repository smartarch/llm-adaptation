A villager sent from the Village at meal age 3 can reach the Cave too late to get a useful attack before needing to return. This version only sends villagers with a recently reset meal clock, and sends Cave villagers home at age 4 so they can eat before starvation. It also keeps food production going when wheat is low and recruits warrior pairs from surplus villagers, without retreating fighters just because they are injured.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        all_villagers = list(environment.warriors) + list(environment.farmers)
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Eat before sending anyone back to the Cave. This avoids starting a
        # trip with too little time left for a meaningful attack.
        eaters = [
            c for c in villagers
            if getattr(c, "steps_since_meal", 0) >= 3
        ]
        eat_ids = {id(c) for c in eaters}

        # Keep one farmer producing when the wheat supply is getting low.
        # If no farmer exists yet, use a farmer pair to spawn one if possible.
        farm_ids = set()
        farmers = [
            c for c in villagers
            if getattr(c, "role", "") == "Farmer"
            and id(c) not in eat_ids
        ]
        if wheat < 18 and farmers:
            farmers.sort(
                key=lambda c: (
                    getattr(c, "hp", 0),
                    -getattr(c, "steps_since_meal", 0),
                ),
                reverse=True,
            )
            farm_ids.add(id(farmers[0]))

        if len(environment.farmers) == 0:
            spawn_group, spawn_cost = "spawn farmer", 10
        else:
            spawn_group, spawn_cost = "spawn warrior", 12

        # Recruit early, but keep a small workforce available to attack and
        # reserve wheat for villagers who need to eat now.
        candidates = [
            c for c in villagers
            if id(c) not in eat_ids
            and id(c) not in farm_ids
            and getattr(c, "steps_since_meal", 0) <= 2
        ]
        candidates.sort(
            key=lambda c: (
                0 if getattr(c, "role", "") == "Farmer" else 1,
                -getattr(c, "hp", 0),
            )
        )

        due_meals = sum(
            1 for c in all_villagers
            if getattr(c, "steps_since_meal", 0) >= 3
        )
        current_warriors = len(environment.warriors)
        spawn_ids = set()

        # Stop investing in new warriors when the Dragon is nearly dead;
        # otherwise recruit when there is enough wheat and a complete pair.
        if (
            dragon_hp > 12
            and (current_warriors < 10 or current_warriors == 0)
            and wheat >= spawn_cost + due_meals
            and len(candidates) >= 2
        ):
            spawn_ids = {id(candidates[0]), id(candidates[1])}

        for c in villagers:
            if id(c) in eat_ids:
                group = "eat"
            elif id(c) in farm_ids:
                group = "farm"
            elif id(c) in spawn_ids:
                group = spawn_group
            elif getattr(c, "steps_since_meal", 0) <= 2:
                group = "cave"
            else:
                # Stay in the Village until fed rather than starting a trip
                # that would provide little or no time to attack.
                group = "eat"

            environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if getattr(c, "steps_since_meal", 0) >= 4:
                group = "village"
            else:
                group = "attack"

            environment.assign_group(c, group)
```