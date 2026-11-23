The proven strategy’s main delay is that surplus farmers stay home until the Dragon is nearly defeated. This version sends those farmers to attack earlier once the Village has a healthy wheat reserve, while keeping the same one-pair-at-a-time spawning, meal priority, and minimum farming workforce. That adds damage without relying on aggressive multi-spawning.

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

        # Feed the hungriest villagers first, with time left for Cave villagers
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

        # Keep a small farming workforce in the Village.
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

        # Spawn one pair at a time, preserving a modest food reserve.
        reserve = max(2, (population + 4) // 5)
        if dragon_hp > 0 and warrior_count < 16 and wheat >= 12 + reserve:
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

        # Send surplus farmers to contribute damage when food reserves allow,
        # or when the Dragon is already sufficiently weakened.
        send_surplus_farmers = wheat >= max(20, population)

        for i, component in enumerate(components):
            if actions[i] is not None:
                continue

            role = getattr(component, "role", "")
            hp = getattr(component, "hp", 0)

            if role == "Farmer":
                if hp > 1 and (
                    dragon_hp <= 60
                    or (send_surplus_farmers and i not in keep_farming)
                ):
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