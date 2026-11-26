from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group_ids, group):
        if group not in group_ids:
            raise ValueError(f"Required group {group!r} is not available")
        environment.assign_group(component, group)

    @staticmethod
    def _attr(component, name, default=0):
        return getattr(component, name, default)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._attr(environment.farm, "wheat", 0))
        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(warriors)
        population = len(warriors) + len(farmers)
        assigned = set()

        # Eat immediately once hunger is becoming significant. In particular,
        # villagers returning from the Cave should be fed before going back.
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
        healthy = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 1
            and self._attr(v, "steps_since_meal", 0) < 4
        ]

        # If there are no Warriors yet, build the initial food stock rather
        # than sending the entire population away from the farm.
        if warrior_count == 0 and wheat < 12:
            for v in remaining:
                self._assign(environment, v, group_ids, "farm")
            return

        # Recruit in pairs whenever the food reserve permits. Avoid spending
        # the last food needed to keep the existing population alive.
        reserve = min(population, 5)
        if warrior_count == 0:
            reserve = 0

        if len(healthy) >= 2 and wheat >= 12 + reserve:
            healthy.sort(
                key=lambda v: (
                    self._attr(v, "steps_since_meal", 0),
                    self._attr(v, "role", "") != "Farmer",
                )
            )
            for v in healthy[:2]:
                self._assign(environment, v, group_ids, "spawn warrior")
                assigned.add(id(v))

        remaining = [v for v in villagers if id(v) not in assigned]

        # Maintain food production when stores are modest. When stores are
        # empty, use all available villagers to rebuild them.
        if wheat <= 5:
            farm_slots = len(remaining)
        elif wheat < 20:
            farm_slots = 1
        else:
            farm_slots = 0

        farm_candidates = [v for v in remaining if self._attr(v, "hp", 0) > 1]
        farm_candidates.sort(
            key=lambda v: (
                self._attr(v, "role", "") != "Farmer",
                self._attr(v, "steps_since_meal", 0),
            )
        )
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

            # Stagger return times slightly to avoid sending the whole fighting
            # force home together. Both thresholds leave time to travel and eat
            # in the Village before the starvation limit.
            threshold = 2 if (id(v) // 16) % 2 == 0 else 3
            if hp <= 1 or age >= threshold:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")