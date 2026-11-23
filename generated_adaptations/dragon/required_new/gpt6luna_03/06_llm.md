The previous strategy’s food reserve could prevent warrior spawning indefinitely, especially with the 15-wheat starting condition. This version keeps farming only when the stock is low, uses surplus wheat to spawn warriors more readily, and sends Cave villagers back to eat at hunger 4 so they have time to travel before starving. It assigns every villager on every call.

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
        warriors = list(environment.warriors)
        population = len(warriors) + len(environment.farmers)
        warrior_count = len(warriors)

        assigned = set()

        # Eat before the villager is sent on a trip or assigned elsewhere.
        for villager in sorted(
            (v for v in villagers if self._hunger(v) >= 4),
            key=self._hunger,
            reverse=True,
        ):
            if wheat <= 0:
                break
            environment.assign_group(villager, "eat")
            assigned.add(id(villager))
            wheat -= 1

        available = [v for v in villagers if id(v) not in assigned]

        # Keep food production going only when the stock is low. Prefer a
        # farmer, but use another villager if no farmer is available.
        if dragon_hp > 0 and wheat < max(10, population):
            worker = next(
                (v for v in available if self._role(v) == "farmer"),
                available[0] if available else None,
            )
            if worker is not None:
                environment.assign_group(worker, "farm")
                assigned.add(id(worker))

        available = [v for v in villagers if id(v) not in assigned]

        # Use affordable pairs to spawn warriors. Keep a small meal buffer,
        # but do not let a large reserve prevent spawning altogether.
        meal_buffer = min(3, population)
        affordable = max(0, (wheat - meal_buffer) // 12)
        warrior_slots = max(0, 12 - warrior_count)
        spawn_pairs = min(len(available) // 2, affordable, warrior_slots)

        for villager in available[: 2 * spawn_pairs]:
            environment.assign_group(villager, "spawn warrior")
            assigned.add(id(villager))

        # Send every remaining villager toward the Cave to contribute damage.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(
                    villager, "cave" if dragon_hp > 0 else "farm"
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        for villager in components:
            # Leave at hunger 4: the trip home takes a step, after which the
            # villager can be assigned to eat in the Village.
            if self._hunger(villager) >= 4 or dragon_hp <= 0:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```