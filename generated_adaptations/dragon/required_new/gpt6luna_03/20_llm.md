The repeated failures suggest the army is not building enough attack damage before the deadline. This version deliberately accumulates a stock of wheat while assigning one villager to farm when reserves are low, then uses surplus wheat to spawn warrior pairs without a fixed population cap. It still feeds hungry villagers first and returns Cave villagers in time to eat.

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
        all_villagers = list(environment.warriors) + list(environment.farmers)
        population = len(all_villagers)

        assigned = set()

        # Feed first, prioritizing villagers closest to starvation.
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

        # Reserve meals due soon, including Cave villagers who are returning.
        due_meals = sum(1 for v in all_villagers if self._hunger(v) >= 3)
        meal_reserve = max(2, due_meals)

        # Build up enough stock to support repeated warrior spawns. A single
        # farmer provides a useful supply without diverting the whole village.
        if dragon_hp > 0 and wheat < 18 and available:
            worker = next(
                (v for v in available if self._role(v) == "farmer"),
                available[0],
            )
            environment.assign_group(worker, "farm")
            assigned.add(id(worker))

        available = [v for v in villagers if id(v) not in assigned]

        # Spawn warriors whenever at least one full spawn cost remains after
        # the meal reserve. Keep spawning while there is time for them to fight.
        if dragon_hp > 0 and step < 27:
            spawn_pairs = min(
                len(available) // 2,
                max(0, (wheat - meal_reserve) // 12),
            )
            for villager in available[: 2 * spawn_pairs]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # Assign every other villager to travel toward the Dragon.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(
                    villager, "cave" if dragon_hp > 0 else "farm"
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        for villager in components:
            # Returning at hunger 4 leaves a step for travel before eating.
            if self._hunger(villager) >= 4 or dragon_hp <= 0:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```