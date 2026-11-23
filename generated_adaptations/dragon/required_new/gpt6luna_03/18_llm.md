To improve damage uptime, don’t keep a farmer assigned to the farm every step when the wheat stock is already healthy. Farm only to replenish a low stock, preserve a real meal buffer before spawning, and concentrate warrior spawning early enough that new warriors can contribute. Villagers in the Cave return at hunger 4; everyone else attacks or travels to attack.

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

        assigned = set()

        # Use the available food to feed those closest to starvation first.
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

        # Keep a reserve for meals, including meals that will come due soon.
        all_villagers = list(environment.warriors) + list(environment.farmers)
        due_soon = sum(1 for v in all_villagers if self._hunger(v) >= 3)
        meal_reserve = max(4, (population + 5) // 6, due_soon)

        # Farm only when the stock is low; otherwise send the potential
        # worker to fight. Prefer farmers, who produce more wheat.
        if dragon_hp > 0 and wheat < meal_reserve + 8 and available:
            worker = next(
                (v for v in available if self._role(v) == "farmer"),
                available[0],
            )
            environment.assign_group(worker, "farm")
            assigned.add(id(worker))

        available = [v for v in villagers if id(v) not in assigned]

        # Spawn early from surplus wheat, using pairs of villagers and
        # retaining enough food for imminent meals.
        if dragon_hp > 0 and step < 12:
            spawn_pairs = min(
                len(available) // 2,
                max(0, (wheat - meal_reserve) // 12),
            )
            for villager in available[: 2 * spawn_pairs]:
                environment.assign_group(villager, "spawn warrior")
                assigned.add(id(villager))

        # Explicitly assign everyone else to travel toward the Cave.
        for villager in villagers:
            if id(villager) not in assigned:
                environment.assign_group(
                    villager, "cave" if dragon_hp > 0 else "farm"
                )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, int(getattr(environment.dragon, "hp", 0)))

        for villager in components:
            if self._hunger(villager) >= 4 or dragon_hp <= 0:
                environment.assign_group(villager, "village")
            else:
                environment.assign_group(villager, "attack")
```