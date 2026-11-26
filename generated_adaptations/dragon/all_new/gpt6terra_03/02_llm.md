The strategy builds up warriors early, then sends them to attack while keeping a villager in the Village to produce food. Cave villagers return when they have gone four steps without a meal, allowing time to travel and eat before six missed steps. It also recruits more warriors when wheat and available villagers permit.

This is a heuristic: the outcome and the feeding requirement cannot be guaranteed for every initial state, especially if there is insufficient wheat or the Dragon’s attacks eliminate villagers.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        population = len(warriors) + len(farmers)
        wheat = max(0, environment.farm.wheat)

        # Default to farming; every villager is explicitly assigned below.
        assignments = ["farm"] * len(villagers)
        unavailable = set()

        # Feed the most urgent villagers first. If food is unavailable, they
        # farm instead, though a missed-meal limit may then be unavoidable.
        urgent = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 5),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in urgent:
            unavailable.add(i)
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        cave_population = sum(
            1 for v in warriors + farmers if v.location == "Cave"
        )
        assault = (
            cave_population > 0
            or environment.dragon.hp < 100
            or len(warriors) >= 4
            or population >= 7
            or step >= 6
        )

        # Keep one village worker behind where possible, preferring a farmer.
        reserve = None
        if population > 1 and villagers:
            village_farmers = [
                i for i, v in enumerate(villagers) if v.role == "Farmer"
            ]
            candidates = village_farmers or list(range(len(villagers)))
            reserve = min(
                candidates,
                key=lambda i: (villagers[i].hp, -villagers[i].steps_since_meal),
            )

        mobile = [
            i for i in range(len(villagers))
            if i != reserve and i not in unavailable
        ]

        # Villagers leaving for the cave need enough time to attack and return
        # before their next required meal.
        if assault:
            for i in mobile:
                if villagers[i].steps_since_meal >= 3:
                    unavailable.add(i)
                    if wheat >= 1:
                        assignments[i] = "eat"
                        wheat -= 1

        # Recruit while there is still time for the new villager to help.
        # Keep some wheat for upcoming meals and never spend the same wheat
        # twice in this assignment pass.
        if step < 16 and len(warriors) < 7:
            spare = [
                i for i in range(len(villagers))
                if i != reserve and i not in unavailable
            ]
            if assault:
                # During combat, do not delay warriors to perform spawning.
                spare = [i for i in spare if villagers[i].role == "Farmer"]

            # Farmers are useful for spawning during an assault; otherwise
            # prefer warriors as spawners so farmers can produce more wheat.
            spare.sort(
                key=lambda i: (
                    villagers[i].role != ("Farmer" if assault else "Warrior"),
                    villagers[i].steps_since_meal,
                )
            )
            food_reserve = min(population, 5)

            while len(spare) >= 2 and wheat >= 12 + food_reserve:
                if len(warriors) >= 7:
                    break
                first, second = spare.pop(0), spare.pop(0)
                assignments[first] = assignments[second] = "spawn warrior"
                unavailable.update((first, second))
                wheat -= 12
                # Track planned births because the observable list is static.
                warriors.append(None)

        if assault:
            for i in mobile:
                if i not in unavailable and villagers[i].steps_since_meal <= 2:
                    assignments[i] = "cave"

        for villager, group in zip(villagers, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            if villager.steps_since_meal >= 4:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(villager, group)
```