The main fixes are to keep Farmers in the Village, reserve wheat for meals before spawning, and send Cave fighters back early enough to travel home and eat before starvation. The strategy also prioritizes spawning Warriors when none exist, while keeping attacks continuous whenever healthy Warriors are available.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        if not villagers:
            return

        assigned = set()
        wheat = max(0, environment.farm.wheat)
        dragon_hp = max(0, environment.dragon.hp)
        population = len(environment.warriors) + len(environment.farmers)
        warriors = list(environment.warriors)
        farmers = list(environment.farmers)

        def hunger(v):
            return getattr(v, "steps_since_meal", 0)

        # Feed first, with a margin before the starvation threshold.
        eat_order = sorted(
            range(len(villagers)),
            key=lambda i: hunger(villagers[i]),
            reverse=True,
        )
        for i in eat_order:
            if hunger(villagers[i]) >= 4 and wheat > 0:
                environment.assign_group(villagers[i], "eat")
                assigned.add(i)
                wheat -= 1

        time_left = 30 - step
        remaining_wheat = max(0, environment.farm.wheat - sum(
            1 for i, v in enumerate(villagers)
            if i in assigned and hunger(v) >= 4
        ))

        # Spawn Warriors early, particularly when there are none. Keep at
        # least one meal per villager in reserve after paying the spawn cost.
        if dragon_hp > 0 and time_left > 1:
            warrior_count = len(warriors)
            farmer_count = len(farmers)
            spawn_group = "spawn warrior"
            spawn_cost = 12

            # If there are no Farmers, recruit one so the Village can sustain
            # its food supply.
            if farmer_count == 0 and warrior_count >= 2:
                spawn_group = "spawn farmer"
                spawn_cost = 10

            meal_reserve = max(1, population)
            can_spawn = remaining_wheat >= spawn_cost + meal_reserve

            if can_spawn:
                available = [
                    i for i in range(len(villagers)) if i not in assigned
                ]

                # Prefer using Farmers for spawning, leaving Warriors free to
                # attack. Still allow any two villagers to spawn if needed.
                available.sort(
                    key=lambda i: (
                        0 if villagers[i].role == "Farmer" else 1,
                        hunger(villagers[i]),
                    )
                )

                if len(available) >= 2:
                    # When a Farmer is the only reliable food producer, retain
                    # one for farm work unless Warriors are urgently needed.
                    if (
                        spawn_group == "spawn warrior"
                        and warrior_count > 0
                        and farmer_count <= 2
                    ):
                        available = [
                            i for i in available
                            if villagers[i].role != "Farmer"
                        ] + [
                            i for i in available
                            if villagers[i].role == "Farmer"
                        ]

                    for i in available[:2]:
                        environment.assign_group(villagers[i], spawn_group)
                        assigned.add(i)

        # Farmers stay in the Village. Keep them working unless they need to
        # eat or are being used to spawn.
        for i, villager in enumerate(villagers):
            if i not in assigned and villager.role == "Farmer":
                environment.assign_group(villager, "farm")
                assigned.add(i)

        # Send remaining Warriors to the Cave. If there is no Farmer available
        # to produce food, use a Warrior to farm when stores are very low.
        remaining_wheat = max(0, environment.farm.wheat - sum(
            1 for i, v in enumerate(villagers)
            if i in assigned and hunger(v) >= 4
        ))
        for i, villager in enumerate(villagers):
            if i in assigned:
                continue
            if remaining_wheat < 2 and villager.role == "Warrior":
                environment.assign_group(villager, "farm")
            else:
                environment.assign_group(villager, "cave")
            assigned.add(i)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, environment.dragon.hp)

        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Return with time for the trip home and a meal before starvation.
            if hunger >= 3 or (hp <= 1 and dragon_hp > 0):
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```