The earlier policies counted farmers as “already farming” based on their location, even though assignments must be repeated each step. That could leave the food supply unsupported. This version explicitly assigns a worker when food is low, reserves wheat for meals due soon, and uses surplus wheat to spawn warrior pairs. Cave villagers head back at hunger 4 and otherwise keep attacking, avoiding avoidable gaps in damage.

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
        population = list(environment.warriors) + list(environment.farmers)
        warrior_count = len(environment.warriors)

        assigned = set()
        ate_ids = set()

        # Eat now when needed. Account for these meals in the available stock.
        for villager in sorted(
            (v for v in villagers if self._hunger(v) >= 4),
            key=self._hunger,
            reverse=True,
        ):
            if wheat < 1:
                break
            environment.assign_group(villager, "eat")
            assigned.add(id(villager))
            ate_ids.add(id(villager))
            wheat -= 1

        available = [v for v in villagers if id(v) not in assigned]

        # Preserve wheat for villagers who will soon need meals, especially
        # Cave villagers already returning for food.
        meals_due = sum(
            1
            for v in population
            if self._hunger(v) >= 3 and id(v) not in ate_ids
        )

        # Reassign a worker explicitly when the food stock is low.
        # Farmers are preferred because they produce more wheat.
        if dragon_hp > 0 and wheat < meals_due + 6 and available:
            worker = next(
                (v for v in available if self._role(v) == "farmer"),
                available[0],
            )
            environment.assign_group(worker, "farm")
            assigned.add(id(worker))
            available = [v for v in available if id(v) != id(worker)]

        # Convert surplus wheat into warriors. Leave the due-meal reserve
        # untouched, and require pairs of villagers for each spawn.
        if dragon_hp > 0 and warrior_count < 10:
            pairs_affordable = max(0, (wheat - meals_due) // 12)
            pairs_available = len(available) // 2
            pairs_needed = max(0, (10 - warrior_count + 1) // 2)
            spawn_pairs = min(pairs_affordable, pairs_available, pairs_needed)

            for villager in available[: 2 * spawn_pairs]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # Every remaining villager heads to the Cave.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(
                    villager, "cave" if dragon_hp > 0 else "farm"
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        for villager in components:
            # A return at hunger 4 allows the one-step trip to the Village
            # before the villager needs to eat.
            if self._hunger(villager) >= 4 or dragon_hp <= 0:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```