The previous policies were too conservative about attacking and could stop replenishing Warriors after casualties. This version sends every healthy villager who is not eating or spawning toward the Cave, lets fighters attack until hunger age 3, and feeds them promptly on return. Farming is primarily used to recover from an empty food supply; when Warriors are depleted, the Village prioritizes farming enough to recruit a pair and then spawns Warriors as soon as the meal reserve allows.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    @staticmethod
    def _attr(component, name, default=0):
        return getattr(component, name, default)

    @staticmethod
    def _assign(environment, component, group_ids, group):
        if group not in group_ids:
            raise ValueError(f"Required group {group!r} is not available")
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._attr(environment.farm, "wheat", 0))
        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(warriors)
        population = len(warriors) + len(farmers)
        assigned = set()

        # Eat as soon as villagers are meaningfully hungry. This gives them
        # time to travel back to the Cave before their next meal is due.
        hungry = sorted(
            (v for v in villagers
             if self._attr(v, "steps_since_meal", 0) >= 3),
            key=lambda v: self._attr(v, "steps_since_meal", 0),
            reverse=True,
        )
        for v in hungry:
            if wheat > 0:
                self._assign(environment, v, group_ids, "eat")
                wheat -= 1
                assigned.add(id(v))

        remaining = [v for v in villagers if id(v) not in assigned]

        # Hold back food expected to be needed by cave villagers returning
        # soon. This is only an estimate; the hunger threshold remains
        # conservative to protect the required meal constraint.
        cave_villagers = [
            v for v in warriors + farmers
            if self._attr(v, "location", "") == "Cave"
        ]
        imminent_meals = sum(
            1 for v in cave_villagers
            if self._attr(v, "steps_since_meal", 0) >= 2
        )

        healthy = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 1
            and self._attr(v, "steps_since_meal", 0) < 5
        ]

        # Replenish the fighting force whenever there are no Warriors. If
        # stores are inadequate, farm until a pair can spawn one.
        if warrior_count == 0 and (wheat < 12 + imminent_meals or len(healthy) < 2):
            for v in remaining:
                if self._attr(v, "hp", 0) <= 1:
                    self._assign(environment, v, group_ids, "farm")
                else:
                    self._assign(environment, v, group_ids, "farm")
            return

        # Spawn Warriors when the pair and cost are available. A larger force
        # is worthwhile because Dragon counterattacks can remove fighters.
        reserve = imminent_meals + min(population, 3)
        should_spawn = (
            len(healthy) >= 2
            and wheat >= 12 + reserve
            and warrior_count < 8
        )
        if should_spawn:
            healthy.sort(
                key=lambda v: (
                    self._attr(v, "steps_since_meal", 0),
                    self._attr(v, "role", "") != "Farmer",
                )
            )
            for v in healthy[:2]:
                self._assign(environment, v, group_ids, "spawn warrior")
                assigned.add(id(v))
            wheat -= 12

        remaining = [v for v in villagers if id(v) not in assigned]

        # Only assign dedicated farm labor when stores are genuinely low.
        # At all other times, healthy villagers should travel to attack.
        if wheat <= 2:
            farm_slots = len(remaining)
        elif wheat < max(7, population + imminent_meals):
            farm_slots = 1
        else:
            farm_slots = 0

        farmers_at_home = [
            v for v in remaining
            if self._attr(v, "role", "") == "Farmer"
            and self._attr(v, "hp", 0) > 1
        ]
        others = [
            v for v in remaining
            if v not in farmers_at_home and self._attr(v, "hp", 0) > 1
        ]
        farm_candidates = farmers_at_home + others
        farm_ids = {id(v) for v in farm_candidates[:farm_slots]}

        for v in remaining:
            if self._attr(v, "hp", 0) <= 1 or id(v) in farm_ids:
                self._assign(environment, v, group_ids, "farm")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for v in components:
            age = self._attr(v, "steps_since_meal", 0)
            hp = self._attr(v, "hp", 0)

            # After three steps without food, start the return journey. The
            # villager arrives in the Village with enough time to eat before
            # the six-step starvation threshold.
            if age >= 3 or hp <= 1:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")
```