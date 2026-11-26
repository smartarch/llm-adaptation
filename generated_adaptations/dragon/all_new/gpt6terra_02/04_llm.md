I removed the killing-blow exception: cave villagers now always return at meal age 4. Warriors also eat before departure when necessary, leaving time for two attacks and a return. Spawning continues longer, with a meal reserve for the whole population.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assignments = ["farm"] * len(villagers)
        wheat = max(0, environment.farm.wheat)

        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        all_villagers = warriors + farmers

        cave_occupied = any(
            villager.location == "Cave" for villager in all_villagers
        )
        assault = (
            environment.dragon.hp < 100
            or cave_occupied
            or len(warriors) >= 4
            or step >= 11
        )

        # Prioritize villagers closest to starvation. Feed potential
        # attackers earlier so they can attack twice before returning.
        feeding_order = sorted(
            range(len(villagers)),
            key=lambda i: villagers[i].steps_since_meal,
            reverse=True,
        )
        for i in feeding_order:
            villager = villagers[i]
            needs_food = villager.steps_since_meal >= 5
            preparing_to_fight = (
                assault
                and villager.role == "Warrior"
                and villager.steps_since_meal >= 2
            )
            late_farmer = (
                step >= 24
                and villager.role == "Farmer"
                and villager.steps_since_meal >= 2
            )
            if wheat >= 1 and (needs_food or preparing_to_fight or late_farmer):
                assignments[i] = "eat"
                wheat -= 1

        # At age 1 or less, a villager can travel, attack twice, and
        # return at age 4 before eating on the following step.
        for i, villager in enumerate(villagers):
            if assignments[i] != "farm" or villager.steps_since_meal > 1:
                continue
            if villager.role == "Warrior" and assault:
                assignments[i] = "cave"
            elif villager.role == "Farmer" and step >= 24:
                assignments[i] = "cave"

        # Reserve one meal per villager, accounting for meals already
        # assigned this step. Do not rely on this step's farm production.
        meals_assigned = sum(action == "eat" for action in assignments)
        reserve = max(0, len(all_villagers) - meals_assigned) + 2
        spawn_budget = max(0, wheat - reserve)

        farmer_count = len(farmers)
        warrior_count = len(warriors)

        while step < 23:
            if farmer_count < 3 and step < 12:
                spawn_group, cost = "spawn farmer", 10
            elif warrior_count < 12:
                spawn_group, cost = "spawn warrior", 12
            else:
                break

            if spawn_budget < cost:
                break

            available = [
                i for i, action in enumerate(assignments) if action == "farm"
            ]
            # Prefer using idle warriors, preserving farmer production.
            available.sort(
                key=lambda i: (
                    villagers[i].role == "Farmer",
                    villagers[i].steps_since_meal,
                )
            )
            if len(available) < 2:
                break

            for i in available[:2]:
                assignments[i] = spawn_group

            spawn_budget -= cost
            if spawn_group == "spawn farmer":
                farmer_count += 1
            else:
                warrior_count += 1

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