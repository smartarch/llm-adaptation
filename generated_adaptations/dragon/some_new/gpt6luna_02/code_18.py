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
        dragon_hp = max(0, self._attr(environment.dragon, "hp", 100))
        warriors = list(getattr(environment, "warriors", []))
        farmers = list(getattr(environment, "farmers", []))
        population = len(warriors) + len(farmers)
        warrior_count = len(warriors)
        assigned = set()

        # Feed before any other use of wheat. Doing this at age 3 gives a
        # margin for travel and for the action timing of the simulation.
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

        # Keep wheat available for villagers due to return from the Cave.
        # They will need a meal shortly after arriving in the Village.
        cave_people = [
            v for v in warriors + farmers
            if self._attr(v, "location", "") == "Cave"
        ]
        returners_due_soon = sum(
            1 for v in cave_people
            if self._attr(v, "steps_since_meal", 0) >= 2
        )
        meal_reserve = returners_due_soon

        final_push = dragon_hp <= 25

        # When there are no Warriors, make sure a pair and the Warrior cost
        # are available before sending villagers away from the Village.
        healthy = [
            v for v in remaining
            if self._attr(v, "hp", 0) > 1
            and self._attr(v, "steps_since_meal", 0) < 5
        ]
        if not final_push and warrior_count == 0 and wheat < 12 + meal_reserve:
            for v in remaining:
                self._assign(environment, v, group_ids, "farm")
            return

        # Turn surplus food into Warriors. Preserve near-term meal needs and
        # one modest additional food buffer rather than repeatedly exhausting
        # the stores.
        can_spawn = (
            not final_push
            and len(healthy) >= 2
            and wheat >= 12 + meal_reserve + min(population, 3)
        )
        if can_spawn:
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

        # Maintain a food-producing workforce when needed. Farmers are
        # preferred, while Warriors are directed toward the Dragon.
        if final_push:
            farm_slots = 0
        elif wheat < max(6, population + meal_reserve):
            farm_slots = 2
        elif wheat < 12 + meal_reserve:
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
            if self._attr(v, "hp", 0) <= 1:
                self._assign(environment, v, group_ids, "farm")
            elif id(v) in farm_ids:
                self._assign(environment, v, group_ids, "farm")
            elif final_push and self._attr(v, "role", "") == "Farmer":
                self._assign(environment, v, group_ids, "cave")
            else:
                self._assign(environment, v, group_ids, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for v in components:
            age = self._attr(v, "steps_since_meal", 0)
            hp = self._attr(v, "hp", 0)

            # Return at age 3 so the villager reaches the Village before the
            # starvation boundary and can eat on the following assignment.
            if age >= 3 or hp <= 1:
                self._assign(environment, v, group_ids, "village")
            else:
                self._assign(environment, v, group_ids, "attack")