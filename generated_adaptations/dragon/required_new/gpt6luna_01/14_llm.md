The latest change sent surplus farmers to the Cave sooner, which reduced wheat production and caused meal-reserve violations. It also made the farming and spawning supply less reliable, contributing to missed wins. I’m reverting to the conservative strategy that passed the earlier tests: prioritize meals, preserve a farming workforce, spawn one pair at a time, and send farmers to attack only when the Dragon is already weakened.

```py
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

        # Feed the hungriest villagers first, leaving time for Cave villagers
        # to return to the Village before starvation.
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

        # Maintain a small farming workforce.
        target_farmers = max(1, (population + 24) // 25) if farmer_count else 0
        available_farmers = [
            i for i, component in enumerate(components)
            if actions[i] is None and getattr(component, "role", "") == "Farmer"
        ]
        available_farmers.sort(
            key=lambda i: getattr(components[i], "hp", 0),
            reverse=True,
        )
        keep_farming = set(available_farmers[:target_farmers])

        # Spawn one pair at a time, and only with wheat above a modest reserve.
        reserve = max(2, (population + 4) // 5)
        if (
            dragon_hp > 0
            and warrior_count < 16
            and wheat >= 12 + reserve
        ):
            candidates = [
                i for i, component in enumerate(components)
                if actions[i] is None
            ]
            surplus_farmers = [
                i for i in candidates
                if getattr(components[i], "role", "") == "Farmer"
                and i not in keep_farming
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
                spawn_candidates += [
                    i for i in candidates
                    if getattr(components[i], "role", "") == "Farmer"
                    and i in keep_farming
                ]

            if len(spawn_candidates) >= 2:
                actions[spawn_candidates[0]] = "spawn warrior"
                actions[spawn_candidates[1]] = "spawn warrior"

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
                actions[i] = "farm"

        self._assign(components, actions, environment)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        actions = []

        for component in components:
            hunger = getattr(component, "steps_since_meal", 0)
            hp = getattr(component, "hp", 0)

            if hunger >= 4 or hp <= 1:
                actions.append("village")
            else:
                actions.append("attack")

        self._assign(components, actions, environment)
```