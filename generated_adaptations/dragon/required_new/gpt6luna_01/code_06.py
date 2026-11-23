from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, components, actions, environment):
        for component, group in zip(components, actions):
            environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        actions = [None] * len(components)

        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))
        population = len(environment.warriors) + len(environment.farmers)
        warrior_count = len(environment.warriors)
        farmer_count = len(environment.farmers)

        # Feed the hungriest villagers first. The threshold leaves room for
        # travel from the Cave before the starvation limit.
        food_remaining = int(wheat)
        by_hunger = sorted(
            range(len(components)),
            key=lambda i: getattr(components[i], "steps_since_meal", 0),
            reverse=True,
        )
        for i in by_hunger:
            if (
                getattr(components[i], "steps_since_meal", 0) >= 4
                and food_remaining > 0
            ):
                actions[i] = "eat"
                food_remaining -= 1

        # Maintain enough farming capacity to keep food production reasonably
        # aligned with population. Farmers staying in the Village are preferred.
        target_farmers = max(1, (population + 24) // 25) if farmer_count else 0
        available_farmers = [
            i for i, c in enumerate(components)
            if actions[i] is None and getattr(c, "role", "") == "Farmer"
        ]
        available_farmers.sort(
            key=lambda i: getattr(components[i], "hp", 0),
            reverse=True,
        )
        keep_farming = set(available_farmers[:target_farmers])

        # Spawn warriors only after reserving food for meals and only when
        # two non-eating villagers can form the required spawn group.
        reserve = max(2, (population + 4) // 5)
        can_spawn = (
            dragon_hp > 0
            and warrior_count < 16
            and wheat >= 12 + reserve
        )

        if can_spawn:
            candidates = [
                i for i, c in enumerate(components)
                if actions[i] is None
            ]

            # Prefer farmers beyond the minimum farming workforce. If the
            # population is small, allow the remaining farmers to spawn too.
            surplus_farmers = [
                i for i in candidates
                if getattr(components[i], "role", "") == "Farmer"
                and i not in keep_farming
            ]
            other_farmers = [
                i for i in candidates
                if getattr(components[i], "role", "") == "Farmer"
                and i in keep_farming
            ]
            village_warriors = [
                i for i in candidates
                if getattr(components[i], "role", "") == "Warrior"
            ]
            village_warriors.sort(
                key=lambda i: getattr(components[i], "hp", 0)
            )

            spawn_candidates = surplus_farmers + village_warriors
            if len(spawn_candidates) < 2:
                spawn_candidates += other_farmers

            if len(spawn_candidates) >= 2:
                for i in spawn_candidates[:2]:
                    actions[i] = "spawn warrior"

        for i, component in enumerate(components):
            if actions[i] is not None:
                continue

            role = getattr(component, "role", "")
            hp = getattr(component, "hp", 0)

            if role == "Farmer":
                if dragon_hp <= 35 and hp > 1:
                    actions[i] = "cave"
                else:
                    actions[i] = "farm"
            elif hp > 1:
                actions[i] = "cave"
            else:
                # A severely injured villager is safer helping produce food.
                actions[i] = "farm"

        self._assign(components, actions, environment)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        actions = [None] * len(components)

        # Villagers at hunger 4 should leave now: travel takes a step, and
        # they can eat as soon as they arrive in the Village.
        for i, component in enumerate(components):
            hunger = getattr(component, "steps_since_meal", 0)
            hp = getattr(component, "hp", 0)

            if hunger >= 4:
                actions[i] = "village"
            elif hp <= 1:
                actions[i] = "village"
            else:
                actions[i] = "attack"

        self._assign(components, actions, environment)