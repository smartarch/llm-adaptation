from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_id, group_ids):
        # Group names are the valid group IDs supplied by the environment.
        if group_id in group_ids:
            environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, environment.farm.wheat)

        farmers = [c for c in villagers if c.role == "Farmer"]
        warriors = [c for c in villagers if c.role == "Warrior"]

        # Eat before reaching six consecutive steps without a meal. Warriors
        # eat earlier because they have just spent a step travelling from Cave.
        needs_meal = [
            c for c in villagers
            if c.steps_since_meal >= (4 if c.role == "Warrior" else 5)
        ]
        needs_meal.sort(key=lambda c: (-c.steps_since_meal, c.hp))

        # Do not assign more meals than the currently available wheat can pay for.
        meal_capacity = int(wheat)
        eating = set()
        for c in needs_meal[:meal_capacity]:
            self._assign(environment, c, "eat", group_ids)
            eating.add(id(c))

        # Warriors that do not need a meal return to the Cave. If wheat is
        # unavailable, a hungry villager stays to work rather than wasting a
        # step attempting to eat.
        for c in warriors:
            if id(c) in eating:
                continue
            if c.steps_since_meal >= 4 and wheat < 1:
                self._assign(environment, c, "farm", group_ids)
            else:
                self._assign(environment, c, "cave", group_ids)

        available_farmers = [c for c in farmers if id(c) not in eating]
        assigned_to_spawn = set()

        # Keep a modest reserve for upcoming meals, in addition to any meals
        # assigned this step.
        safety_reserve = max(2, (len(villagers) + 4) // 5)
        meal_cost = len(eating)

        # When the farming workforce is very small, an early Farmer can improve
        # future food production. Otherwise, spend spawn capacity on Warriors.
        spawn_farmer_first = (
            step <= 4
            and len(farmers) <= 2
            and len(available_farmers) >= 2
            and wheat >= meal_cost + safety_reserve + 10
        )

        if spawn_farmer_first:
            pair = available_farmers[:2]
            for c in pair:
                self._assign(environment, c, "spawn farmer", group_ids)
                assigned_to_spawn.add(id(c))

        remaining_farmers = [
            c for c in available_farmers if id(c) not in assigned_to_spawn
        ]

        # Normally leave at least one Farmer farming. Spend the last pair only
        # when the wheat reserve is especially comfortable.
        if len(remaining_farmers) >= 3:
            pair_limit = (len(remaining_farmers) - 1) // 2
        elif len(remaining_farmers) >= 2 and wheat >= meal_cost + safety_reserve + 40:
            pair_limit = 1
        else:
            pair_limit = 0

        warrior_pairs = 0
        for pair_index in range(pair_limit):
            start = pair_index * 2
            pair = remaining_farmers[start:start + 2]
            required_wheat = meal_cost + safety_reserve + 12 * (pair_index + 1)
            if wheat < required_wheat:
                break

            for c in pair:
                self._assign(environment, c, "spawn warrior", group_ids)
                assigned_to_spawn.add(id(c))
            warrior_pairs += 1

        # Explicitly assign every remaining Farmer.
        for c in farmers:
            if id(c) not in eating and id(c) not in assigned_to_spawn:
                self._assign(environment, c, "farm", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers are more useful producing food in the Village.
                self._assign(environment, c, "village", group_ids)
            elif c.steps_since_meal >= 4:
                # Leave time to travel home and eat before the sixth missed meal.
                self._assign(environment, c, "village", group_ids)
            else:
                self._assign(environment, c, "attack", group_ids)