The key correction is to send **every** Cave villager back as soon as their hunger reaches 4; batching returns can leave someone in the Cave too long. In the Village, feed hungry villagers first, keep a farmer working when the wheat reserve is low, and spend only surplus wheat on spawning warriors. Everyone else attacks or travels toward the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    @staticmethod
    def _hunger(villager):
        return int(getattr(villager, "steps_since_meal", 0))

    @staticmethod
    def _role(villager):
        return str(getattr(villager, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        if not villagers:
            return

        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))
        population = len(environment.warriors) + len(environment.farmers)
        warrior_count = len(environment.warriors)

        assigned = set()

        # Feed anyone approaching the starvation limit before allocating
        # villagers to travel, farm, or spawn.
        hungry = sorted(
            (v for v in villagers if self._hunger(v) >= 4),
            key=self._hunger,
            reverse=True,
        )
        for villager in hungry:
            if wheat < 1:
                break
            environment.assign_group(villager, "eat")
            assigned.add(id(villager))
            wheat -= 1

        remaining = [v for v in villagers if id(v) not in assigned]

        # Maintain food production when the stock is getting low. Prefer
        # farmers, who produce more wheat.
        farm_target = 0
        if dragon_hp > 0 and wheat < max(12, 2 * population):
            farm_target = max(1, (population + 19) // 20)

        farmers = [v for v in remaining if self._role(v) == "farmer"]
        workers = farmers[:farm_target]
        if len(workers) < farm_target:
            others = [v for v in remaining if v not in workers]
            workers.extend(others[:farm_target - len(workers)])

        for villager in workers:
            environment.assign_group(villager, "farm")
            assigned.add(id(villager))

        remaining = [v for v in villagers if id(v) not in assigned]

        # Spawn warriors from surplus wheat, retaining a food buffer so that
        # spawning does not leave the population without meals.
        food_buffer = max(4, population)
        if dragon_hp > 0 and warrior_count < 8 and wheat >= 12 + food_buffer:
            spawn_slots = min(8 - warrior_count, len(remaining) // 2)
            spawn_slots = max(0, spawn_slots)
            for villager in remaining[: 2 * spawn_slots]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # Explicitly assign every other villager, including those who should
        # keep traveling toward the Cave.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(villager, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        for villager in components:
            # They need a full step to travel back before they can eat.
            # Returning at hunger 4 keeps them from reaching the starvation
            # threshold while they are still in the Cave.
            if self._hunger(villager) >= 4:
                environment.assign_group(villager, "village")
            elif dragon_hp > 0:
                environment.assign_group(villager, "attack")
            else:
                environment.assign_group(villager, "village")
```