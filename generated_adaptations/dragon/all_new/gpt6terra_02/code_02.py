from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        assignments = ["farm"] * len(villagers)
        wheat = max(0, environment.farm.wheat)

        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        all_villagers = warriors + farmers

        cave_occupied = any(v.location == "Cave" for v in all_villagers)
        assault = (
            environment.dragon.hp < 100
            or cave_occupied
            or len(warriors) >= 4
            or step >= 11
        )

        # Feed those with the most urgent need first. Warriors preparing
        # to depart eat earlier so that they have time to attack and return.
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
                and villager.steps_since_meal >= 3
            )
            late_farmer = (
                step >= 24
                and villager.role == "Farmer"
                and villager.steps_since_meal >= 3
            )
            if wheat >= 1 and (needs_food or preparing_to_fight or late_farmer):
                assignments[i] = "eat"
                wheat -= 1

        # A departure at meal age 2 or less leaves time for a cave attack
        # and a return before the next meal is due.
        for i, villager in enumerate(villagers):
            if assignments[i] != "farm" or villager.steps_since_meal > 2:
                continue
            if villager.role == "Warrior" and assault:
                assignments[i] = "cave"
            elif villager.role == "Farmer" and step >= 24:
                assignments[i] = "cave"

        # Keep wheat for villagers who will soon need meals, including
        # those returning from the cave. Assignments are not assumed to
        # change the observable state during this method.
        upcoming_meals = sum(
            1 for v in all_villagers if v.steps_since_meal >= 3
        )
        meals_assigned = sum(1 for action in assignments if action == "eat")
        reserve = max(0, upcoming_meals - meals_assigned) + 2
        spawn_budget = max(0, wheat - reserve)

        farmer_count = len(farmers)
        warrior_count = len(warriors)

        # Grow the economy early, then build an attacking force. Spawners
        # are taken from villagers who would otherwise farm.
        while step < 20:
            if farmer_count < 3 and step < 12:
                spawn_group, cost = "spawn farmer", 10
            elif warrior_count < 8:
                spawn_group, cost = "spawn warrior", 12
            else:
                break

            if spawn_budget < cost:
                break

            available = [
                i for i, action in enumerate(assignments) if action == "farm"
            ]
            available.sort(
                key=lambda i: (
                    villagers[i].role == "Farmer",
                    villagers[i].steps_since_meal,
                )
            )
            if len(available) < 2:
                break

            pair = available[:2]
            remaining_farmers = sum(
                1
                for i in available
                if i not in pair and villagers[i].role == "Farmer"
            )
            # Normally retain a farmer to produce food. With only two
            # villagers, allow both to spawn so the population can grow.
            if len(villagers) > 2 and farmer_count > 0 and remaining_farmers == 0:
                break

            for i in pair:
                assignments[i] = spawn_group
            spawn_budget -= cost
            if spawn_group == "spawn farmer":
                farmer_count += 1
            else:
                warrior_count += 1

        for villager, group in zip(villagers, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)

        # Villagers at age 4 can attack safely this step, but normally
        # must return now to eat before six consecutive missed meals.
        possible_damage = sum(
            3 if v.role == "Warrior" else 1
            for v in villagers
            if v.steps_since_meal <= 4
        )
        can_finish = possible_damage >= environment.dragon.hp

        for villager in villagers:
            if villager.steps_since_meal <= 3:
                group = "attack"
            elif villager.steps_since_meal == 4 and can_finish:
                group = "attack"
            else:
                group = "village"
            environment.assign_group(villager, group)