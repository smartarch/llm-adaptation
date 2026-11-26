The earlier versions either spent too many turns farming/recruiting or let fighters wait too long to eat. This version uses a short, staggered return cycle, feeds villagers as soon as they are in the Village and hungry, and recruits Warriors whenever a pair and the wheat cost are available. Farming is a temporary response to low stores; otherwise healthy villagers are sent to attack.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._slots = {}
        self._next_slot = 0

    def _slot(self, component):
        key = id(component)
        if key not in self._slots:
            self._slots[key] = self._next_slot
            self._next_slot += 1
        return self._slots[key]

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
        population = len(warriors) + len(farmers)
        warrior_count = len(warriors)
        assigned = set()

        # Eat immediately in the Village rather than risk another travel step.
        hungry = sorted(
            (v for v in villagers if self._attr(v, "steps_since_meal", 0) >= 3),
            key=lambda v: self._attr(v, "steps_since_meal", 0),
            reverse=True,
        )
        for v in hungry:
            if wheat > 0:
                self._assign(environment, v, group_ids, "eat")
                wheat -= 1
                assigned.add(id(v))

        remaining = [v for v in villagers if id(v) not in assigned]

        # When there is not enough wheat for a Warrior, produce food first.
        # This is especially important at the start of no-warrior games.
        if wheat < 12 and warrior_count == 0:
            for v in remaining:
                self._assign(environment, v, group_ids, "farm")
            return

        # Recruit in pairs. Warriors are the best use of spare wheat for
        # killing the Dragon, so do not stop at a small fixed target.
        healthy = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 0
            and self._attr(v, "steps_since_meal", 0) < 5
        ]
        if len(healthy) >= 2 and wheat >= 12:
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

        # Rebuild the food reserve with a small workforce when needed. If
        # wheat is completely exhausted, use everyone available to farm.
        if wheat <= 0:
            farm_slots = len(remaining)
        elif wheat < max(6, population):
            farm_slots = 2
        elif wheat < 18:
            farm_slots = 1
        else:
            farm_slots = 0

        candidates = [v for v in remaining if self._attr(v, "hp", 0) > 0]
        candidates.sort(
            key=lambda v: (
                self._attr(v, "role", "") != "Farmer",
                self._attr(v, "steps_since_meal", 0),
            )
        )
        farm_ids = {id(v) for v in candidates[:farm_slots]}

        for v in remaining:
            self._slot(v)
            if self._attr(v, "hp", 0) <= 0 or id(v) in farm_ids:
                self._assign(environment, v, group_ids, "farm")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for v in components:
            slot = self._slot(v)
            age = self._attr(v, "steps_since_meal", 0)

            # Two staggered return schedules reduce the chance that the whole
            # fighting force leaves the Cave together. Both return early
            # enough to reach the Village and eat before the starvation limit.
            return_age = 2 if slot % 2 == 0 else 3
            if age >= return_age:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")
```