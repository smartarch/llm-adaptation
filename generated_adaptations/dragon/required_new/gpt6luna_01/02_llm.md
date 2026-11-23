The strategy prioritizes meals before any other village action, then keeps enough farmers working to sustain the population. When wheat is plentiful, it uses two villagers to spawn a warrior, with a cap to avoid draining the food supply. Healthy warriors go to the Cave and attack; cave villagers return to eat before hunger becomes dangerous, or retreat at critically low health. Farmers already in the Cave also attack, and village farmers join the attack when the Dragon is close to death. Every villager is explicitly assigned on every call. 

```py
import abc
import math

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
        total_farmers = len(environment.farmers)
        total_warriors = len(environment.warriors)

        # Feed the villagers who are closest to missing their required meal.
        hungry = sorted(
            range(len(components)),
            key=lambda i: getattr(components[i], "steps_since_meal", 0),
            reverse=True,
        )
        food_left = int(wheat)
        for i in hungry:
            if getattr(components[i], "steps_since_meal", 0) >= 4 and food_left > 0:
                actions[i] = "eat"
                food_left -= 1

        eaten_farmer_count = sum(
            1
            for i, component in enumerate(components)
            if actions[i] == "eat" and getattr(component, "role", "") == "Farmer"
        )

        # Roughly one continuously farming farmer can feed up to 30 villagers.
        farmer_floor = math.ceil(population / 30) if total_farmers else 0
        available_wheat = max(0, wheat - food_left + 0)  # Keep the observed stock for the spawn check.
        can_spawn = (
            dragon_hp > 20
            and total_warriors < 10
            and wheat >= 12 + max(4, math.ceil(population / 2))
        )

        if can_spawn:
            candidates = []
            non_eating_farmers = sum(
                1
                for i, component in enumerate(components)
                if actions[i] != "eat" and getattr(component, "role", "") == "Farmer"
            )
            surplus_farmers = max(0, non_eating_farmers - farmer_floor)

            for i, component in enumerate(components):
                if actions[i] is not None:
                    continue
                role = getattr(component, "role", "")
                hp = getattr(component, "hp", 0)

                # Prefer villagers who are less valuable as immediate attackers.
                if role == "Warrior":
                    candidates.append((0 if hp <= 2 else 1, i))
                elif role == "Farmer" and surplus_farmers > 0:
                    candidates.append((2, i))
                    surplus_farmers -= 1

            candidates.sort()
            if len(candidates) >= 2:
                actions[candidates[0][1]] = "spawn warrior"
                actions[candidates[1][1]] = "spawn warrior"

        # Send healthy warriors to the Cave. Keep critically injured warriors
        # in the Village rather than exposing them to another Dragon attack.
        for i, component in enumerate(components):
            if actions[i] is not None:
                continue

            role = getattr(component, "role", "")
            hp = getattr(component, "hp", 0)

            if role == "Warrior":
                actions[i] = "cave" if hp > 1 else "farm"
            elif role == "Farmer":
                # In the endgame, extra farmers can help finish the Dragon.
                if dragon_hp <= 18 and hp > 1:
                    actions[i] = "cave"
                else:
                    actions[i] = "farm"
            else:
                actions[i] = "farm"

        self._assign(components, actions, environment)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        actions = [None] * len(components)

        for i, component in enumerate(components):
            hp = getattr(component, "hp", 0)
            hunger = getattr(component, "steps_since_meal", 0)

            # A villager needs time to travel back to the Village and eat.
            # Returning at hunger 4 leaves a safe margin before starvation.
            if hunger >= 4 or hp <= 1:
                actions[i] = "village"
            else:
                actions[i] = "attack"

        self._assign(components, actions, environment)
```