from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, components, group_id):
        for component in components:
            environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        if not components:
            return

        assigned = set()
        wheat = max(0, environment.farm.wheat)
        dragon_hp = max(0, environment.dragon.hp)
        villagers = list(components)

        def hunger(v):
            return getattr(v, "steps_since_meal", 0)

        # Feed the hungriest villagers first. Feeding at five steps leaves a
        # margin before starvation begins.
        eaters = sorted(
            (i for i, v in enumerate(villagers) if hunger(v) >= 5),
            key=lambda i: hunger(villagers[i]),
            reverse=True,
        )
        for i in eaters:
            if wheat <= 0:
                break
            environment.assign_group(villagers[i], "eat")
            assigned.add(i)
            wheat -= 1

        remaining_wheat = max(0, environment.farm.wheat - (len(assigned)))

        # Keep a farmer working. When stores are low, use extra farmers to
        # rebuild the food reserve.
        farmers = [
            i for i, v in enumerate(villagers)
            if i not in assigned and v.role == "Farmer"
        ]
        farm_target = 1
        if remaining_wheat < 12:
            farm_target = 2
        if remaining_wheat == 0:
            farm_target = len(farmers)

        farmers.sort(key=lambda i: hunger(villagers[i]))
        for i in farmers[:farm_target]:
            environment.assign_group(villagers[i], "farm")
            assigned.add(i)

        # Spawning is worthwhile early, but preserve wheat for meals and
        # avoid spending a turn spawning when the Dragon is nearly defeated.
        time_left = 30 - step
        if dragon_hp > 8 and time_left > 2:
            spawn_role = "spawn farmer" if not environment.farmers else "spawn warrior"
            spawn_cost = 10 if spawn_role == "spawn farmer" else 12
            population = len(environment.warriors) + len(environment.farmers)
            meal_reserve = max(2, min(6, (population + 5) // 6))
            spawn_budget = max(0, environment.farm.wheat - meal_reserve)
            pairs = min(
                sum(1 for i in range(len(villagers)) if i not in assigned) // 2,
                spawn_budget // spawn_cost,
            )

            # Prefer using Farmers for spawning where possible, since they
            # deal less damage than Warriors when sent to the Cave.
            available = [
                i for i in range(len(villagers)) if i not in assigned
            ]
            available.sort(
                key=lambda i: (
                    0 if villagers[i].role == "Farmer" else 1,
                    hunger(villagers[i]),
                )
            )
            for i in available[: pairs * 2]:
                environment.assign_group(villagers[i], spawn_role)
                assigned.add(i)

        # Send all remaining villagers to the Cave; Warriors are especially
        # valuable there, but Farmers can still contribute damage.
        remaining = [i for i in range(len(villagers)) if i not in assigned]
        remaining.sort(
            key=lambda i: (
                0 if villagers[i].role == "Warrior" else 1,
                hunger(villagers[i]),
            )
        )
        for i in remaining:
            environment.assign_group(villagers[i], "cave")
            assigned.add(i)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, environment.dragon.hp)

        for villager in components:
            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Return early enough to travel to the Village and eat before
            # reaching six consecutive steps without a meal. Retreat fragile
            # villagers as well, unless their attack can finish the Dragon.
            must_return_for_food = hunger >= 4
            must_retreat = hp <= 1 and dragon_hp > 0

            if must_return_for_food or must_retreat:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")