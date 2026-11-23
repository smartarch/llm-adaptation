To try to reduce the win time without sacrificing the food supply, this version can spawn multiple warriors in one step when wheat and villagers allow it. It keeps at least one farmer working, prioritizes meals, and sends surplus farmers to attack once the wheat reserve is healthy or the Dragon is weakened. Cave villagers still return before hunger becomes critical.

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

        # Feed villagers at risk first; the reserve leaves time for a Cave-to-
        # Village trip before starvation.
        food_remaining = int(wheat)
        hungry = sorted(
            range(len(components)),
            key=lambda i: getattr(components[i], "steps_since_meal", 0),
            reverse=True,
        )
        for i in hungry:
            if (
                getattr(components[i], "steps_since_meal", 0) >= 4
                and food_remaining > 0
            ):
                actions[i] = "eat"
                food_remaining -= 1

        # Keep at least one local farmer working. More may be kept for larger
        # populations, but surplus farmers can help spawn or attack.
        target_farmers = max(1, (population + 24) // 25) if farmer_count else 0
        farmers_available = [
            i for i, c in enumerate(components)
            if actions[i] is None and getattr(c, "role", "") == "Farmer"
        ]
        farmers_available.sort(
            key=lambda i: getattr(components[i], "hp", 0),
            reverse=True,
        )
        keep_farming = set(farmers_available[:target_farmers])

        # Spend only wheat above a food reserve. Multiple pairs can spawn
        # warriors in the same step when both wheat and villagers are available.
        food_reserve = max(4, population // 2)
        spawn_budget = max(0, food_remaining - food_reserve)
        spawn_pairs = min(
            spawn_budget // 12,
            max(0, (16 - warrior_count + 1) // 2),
        )

        surplus_farmers = [
            i for i in farmers_available
            if i not in keep_farming
        ]
        candidates = list(surplus_farmers)

        # If surplus farmers are insufficient, use other farmers before
        # diverting healthy warriors from attacking.
        other_farmers = [
            i for i in farmers_available
            if i in keep_farming
        ]
        candidates.extend(other_farmers)

        for pair in range(spawn_pairs):
            first = pair * 2
            second = first + 1
            if second >= len(candidates):
                break
            actions[candidates[first]] = "spawn warrior"
            actions[candidates[second]] = "spawn warrior"

        for i, component in enumerate(components):
            if actions[i] is not None:
                continue

            role = getattr(component, "role", "")
            hp = getattr(component, "hp", 0)

            if role == "Farmer":
                surplus_stock = wheat >= max(12, population)
                if hp > 1 and (dragon_hp <= 60 or surplus_stock):
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