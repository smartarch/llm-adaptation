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

        # Feed promptly after return from the Cave. At hunger age 3, eating
        # now leaves a margin for any timing differences in the simulation.
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

        # If the stores are empty, work the farm rather than sending hungry
        # villagers on another trip. This replenishes food for the next call.
        if wheat == 0:
            for v in remaining:
                self._assign(environment, v, group_ids, "farm")
            return

        eligible = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 1
            and self._attr(v, "steps_since_meal", 0) < 3
        ]

        # Spawn Warriors as soon as possible when there are none. Once a
        # fighting force exists, retain a small reserve for meals before
        # recruiting further.
        if warrior_count < 4 and len(eligible) >= 2:
            reserve = 0 if warrior_count == 0 else min(population, 4)
            if wheat >= 12 + reserve:
                eligible.sort(
                    key=lambda v: (
                        self._attr(v, "steps_since_meal", 0),
                        self._attr(v, "role", "") != "Farmer",
                    )
                )
                for v in eligible[:2]:
                    self._assign(environment, v, group_ids, "spawn warrior")
                    assigned.add(id(v))
                wheat -= 12

        remaining = [v for v in villagers if id(v) not in assigned]

        # Keep only a limited workforce at home when stores are low; otherwise
        # send healthy villagers to the Cave to maintain pressure on the Dragon.
        if wheat < 8:
            farm_slots = 2
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
            if id(v) in assigned:
                continue
            if self._attr(v, "hp", 0) <= 1 or id(v) in farm_ids:
                self._assign(environment, v, group_ids, "farm")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for v in components:
            age = self._attr(v, "steps_since_meal", 0)
            hp = self._attr(v, "hp", 0)

            # Return early enough to travel to the Village and eat before the
            # starvation threshold. Healthy villagers attack on other turns.
            if age >= 3 or hp <= 1:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")