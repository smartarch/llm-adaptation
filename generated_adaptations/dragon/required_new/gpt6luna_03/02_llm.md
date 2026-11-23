Keep enough villagers farming to sustain food, feed villagers before they reach the starvation threshold, and send available warriors to the Cave promptly. Use surplus farmers to spawn warriors when there is enough wheat and the warrior count is still small. In the Cave, attack with everyone who can deal damage, while rotating hungry villagers back to the Village in small batches so the attack can continue.

```py
import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _hunger(component):
        return int(getattr(component, "steps_since_meal", 0))

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))
        population = len(environment.warriors) + len(environment.farmers)

        # Feed the hungriest villagers first, while there is food available.
        hungry = sorted(
            (v for v in villagers if self._hunger(v) >= 4),
            key=self._hunger,
            reverse=True,
        )
        assigned = set()
        for villager in hungry:
            if wheat < 1:
                break
            environment.assign_group(villager, "eat")
            assigned.add(id(villager))
            wheat -= 1

        remaining = [v for v in villagers if id(v) not in assigned]

        # Keep a small farming workforce when the food stock is low.
        # One farmer can provide substantial food for the population.
        low_food = wheat < max(20, 2 * population)
        farm_target = (
            max(1, math.ceil(max(1, population) / 25))
            if low_food and dragon_hp > 15
            else 0
        )
        farmers = [v for v in remaining if self._role(v) == "farmer"]
        workers = farmers[:farm_target]
        if len(workers) < farm_target:
            workers += [
                v for v in remaining
                if self._role(v) != "farmer" and v not in workers
            ][:farm_target - len(workers)]

        for villager in workers:
            environment.assign_group(villager, "farm")
            assigned.add(id(villager))

        remaining = [v for v in remaining if id(v) not in assigned]

        # Spend surplus wheat to create warriors, using surplus farmers rather
        # than delaying warriors who can already travel to the Cave.
        warrior_count = len(environment.warriors)
        reserve = population  # keep a meal in reserve for each living villager
        if dragon_hp > 15 and warrior_count < 6 and wheat >= 12 + reserve:
            surplus_farmers = [
                v for v in remaining if self._role(v) == "farmer"
            ]
            spawn_count = min(
                len(surplus_farmers) // 2 * 2,
                2 * (6 - warrior_count),
            )
            for villager in surplus_farmers[:spawn_count]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # Send everyone not assigned to eat, farm, or spawn toward the Dragon.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)
        if not villagers:
            return

        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        # Stagger trips back to the Village for meals. The batch size gives
        # villagers time to travel, eat, and return without all leaving at once.
        meal_batch = max(1, math.ceil(len(villagers) / 5))
        eligible = sorted(
            (v for v in villagers if self._hunger(v) >= 3),
            key=self._hunger,
            reverse=True,
        )
        forced = [v for v in eligible if self._hunger(v) >= 5]
        returning = {id(v) for v in forced}
        for villager in eligible:
            if len(returning) >= meal_batch:
                break
            returning.add(id(villager))

        for villager in villagers:
            if id(villager) in returning:
                environment.assign_group(villager, "village")
            elif dragon_hp > 0 and self._hunger(villager) < 6:
                environment.assign_group(villager, "attack")
            else:
                # A hungry villager cannot damage the Dragon; send them home
                # rather than leave them idle in the Cave.
                environment.assign_group(villager, "village")
```