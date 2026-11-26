The previous policies either rotated fighters out too early or spent too much time on farming and recruitment, leaving too little sustained damage to finish the Dragon. This version recruits an initial pair of Warriors when needed, then prioritizes Cave attacks. It staggers returns at hunger ages 3–4 and feeds returning villagers promptly, while farming more aggressively only when wheat is scarce.  
```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._component_slots = {}
        self._next_slot = 0

    @staticmethod
    def _attr(component, name, default=0):
        return getattr(component, name, default)

    @staticmethod
    def _assign(environment, component, group_ids, group):
        if group not in group_ids:
            raise ValueError(f"Required group {group!r} is not available")
        environment.assign_group(component, group)

    def _slot(self, component):
        key = id(component)
        if key not in self._component_slots:
            self._component_slots[key] = self._next_slot
            self._next_slot += 1
        return self._component_slots[key]

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._attr(environment.farm, "wheat", 0))
        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(warriors)
        population = len(warriors) + len(farmers)
        assigned = set()

        # Feed villagers before sending them back out. Age four is a
        # conservative threshold that preserves a margin before starvation.
        hungry = sorted(
            (v for v in villagers
             if self._attr(v, "steps_since_meal", 0) >= 4),
            key=lambda v: self._attr(v, "steps_since_meal", 0),
            reverse=True,
        )
        for v in hungry:
            if wheat > 0:
                self._assign(environment, v, group_ids, "eat")
                wheat -= 1
                assigned.add(id(v))

        remaining = [v for v in villagers if id(v) not in assigned]

        # Build enough food to create the first Warriors if the game starts
        # without any. Do not send the entire population away before recruitment.
        if warrior_count == 0 and wheat < 12:
            for v in remaining:
                self._assign(environment, v, group_ids, "farm")
            return

        healthy = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 1
            and self._attr(v, "steps_since_meal", 0) < 5
        ]

        # Recruit up to two Warriors early, then spend the remaining turns
        # attacking rather than continuously expanding the population.
        if warrior_count < 2 and len(healthy) >= 2 and wheat >= 12:
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

        # Farm only when needed to maintain a meal supply; at zero wheat,
        # prioritize food production.
        if wheat <= 0:
            farm_slots = len(remaining)
        elif wheat < max(6, population):
            farm_slots = 2
        elif wheat < 12:
            farm_slots = 1
        else:
            farm_slots = 0

        farm_candidates = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 1
        ]
        farm_candidates.sort(
            key=lambda v: (
                self._attr(v, "role", "") != "Farmer",
                self._attr(v, "steps_since_meal", 0),
            )
        )
        farm_ids = {id(v) for v in farm_candidates[:farm_slots]}

        for v in remaining:
            self._slot(v)
            if self._attr(v, "hp", 0) <= 1 or id(v) in farm_ids:
                self._assign(environment, v, group_ids, "farm")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for v in components:
            age = self._attr(v, "steps_since_meal", 0)
            hp = self._attr(v, "hp", 0)

            # Stagger the trip back to reduce simultaneous time away from
            # attacking. Returning at age 3 or 4 allows time to travel and eat.
            return_age = 3 + (self._slot(v) % 2)
            if age >= return_age or hp <= 1:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")
```