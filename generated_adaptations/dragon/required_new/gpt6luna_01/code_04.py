from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign_all(self, components, actions, environment):
        for component, group in zip(components, actions):
            environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        actions = [None] * len(components)
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)
        warrior_count = len(all_warriors)
        population = warrior_count + len(all_farmers)

        # Eat early enough to allow a safe return from the Cave and avoid starvation.
        food_left = int(wheat)
        hungry_indices = sorted(
            range(len(components)),
            key=lambda i: getattr(components[i], "steps_since_meal", 0),
            reverse=True,
        )
        for i in hungry_indices:
            if (
                getattr(components[i], "steps_since_meal", 0) >= 3
                and food_left > 0
            ):
                actions[i] = "eat"
                food_left -= 1

        # Spawn warriors whenever the food and available pair permit it. Prefer
        # surplus farmers, keeping one farmer available to produce wheat.
        spawn_pair = []
        if dragon_hp > 0 and warrior_count < 10 and population < 18:
            spawnable = [
                i for i, c in enumerate(components)
                if actions[i] is None
            ]
            farmers_here = [
                i for i in spawnable
                if getattr(components[i], "role", "") == "Farmer"
            ]
            warriors_here = [
                i for i in spawnable
                if getattr(components[i], "role", "") == "Warrior"
            ]

            # Reserve one local farmer when possible. If only two villagers are
            # available, allow both to spawn for a turn rather than never spawning.
            if len(farmers_here) >= 3:
                farmers_here = farmers_here[1:]

            candidates = farmers_here + sorted(
                warriors_here,
                key=lambda i: getattr(components[i], "hp", 0),
            )

            if food_left >= 12 and len(candidates) >= 2:
                spawn_pair = candidates[:2]
                for i in spawn_pair:
                    actions[i] = "spawn warrior"

        # Keep a local farmer working whenever one remains available.
        available_farmers = [
            i for i, c in enumerate(components)
            if actions[i] is None and getattr(c, "role", "") == "Farmer"
        ]
        farmer_keeper = None
        if available_farmers:
            farmer_keeper = max(
                available_farmers,
                key=lambda i: getattr(components[i], "hp", 0),
            )
            actions[farmer_keeper] = "farm"

        # Warriors are the main source of damage. In the endgame, send every
        # remaining healthy villager to help finish the Dragon.
        for i, component in enumerate(components):
            if actions[i] is not None:
                continue

            role = getattr(component, "role", "")
            hp = getattr(component, "hp", 0)

            if role == "Warrior":
                actions[i] = "cave" if hp > 1 else "farm"
            elif dragon_hp <= 20 and hp > 1:
                actions[i] = "cave"
            else:
                actions[i] = "farm"

        self._assign_all(components, actions, environment)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        actions = [None] * len(components)

        village_farmers = sum(
            1 for farmer in environment.farmers
            if getattr(farmer, "location", "") == "Village"
        )

        # If no farmer is currently in the Village, send one back to maintain
        # food production. Otherwise, keep Cave villagers attacking until they
        # need to return for a meal or are too injured to risk.
        farmer_sent_back = False
        for i, component in enumerate(components):
            hp = getattr(component, "hp", 0)
            hunger = getattr(component, "steps_since_meal", 0)
            role = getattr(component, "role", "")

            if role == "Farmer" and village_farmers == 0 and not farmer_sent_back:
                actions[i] = "village"
                farmer_sent_back = True
            elif hunger >= 3 or hp <= 2:
                actions[i] = "village"
            else:
                actions[i] = "attack"

        self._assign_all(components, actions, environment)