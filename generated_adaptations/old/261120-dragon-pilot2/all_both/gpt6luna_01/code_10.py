from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_batches = 0
        self._farmer_spawn_batches = 0
        self._return_cursor = 0

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _hunger(component):
        return int(getattr(component, "steps_since_meal", 0))

    @staticmethod
    def _hp(component):
        return int(getattr(component, "hp", 1))

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))
        assignments = {}

        for component in components:
            role = self._role(component)
            hunger = self._hunger(component)

            if role == "warrior":
                # Eat in the Village before travelling back to the Cave.
                assignments[component] = "eat" if hunger >= 3 else "cave"
            else:
                assignments[component] = "farm"

        # Feed villagers at immediate risk first. Do not assign more meals
        # than can be paid for with the currently available wheat.
        meal_candidates = [
            c for c in components
            if self._hunger(c) >= (
                3 if self._role(c) == "warrior" else 5
            )
        ]
        meal_candidates.sort(
            key=lambda c: (
                self._hunger(c),
                self._role(c) == "warrior",
            ),
            reverse=True,
        )

        for component in meal_candidates:
            if wheat <= 0:
                break
            if assignments[component] != "eat":
                assignments[component] = "eat"
                wheat -= 1

        def spawn_batch(kind, cost):
            nonlocal wheat

            if wheat < cost:
                return False

            if kind == "warrior":
                if self._warrior_spawn_batches >= 2:
                    return False
                spawn_group = "spawn warrior"
            else:
                if self._farmer_spawn_batches >= 1:
                    return False
                spawn_group = "spawn farmer"

            # Do not use villagers assigned to eat or already assigned to
            # another spawn batch.
            candidates = [
                c for c in components
                if assignments[c] in ("farm", "cave")
            ]
            candidates.sort(
                key=lambda c: (
                    self._role(c) != "farmer",
                    self._hunger(c),
                )
            )
            if len(candidates) < 2:
                return False

            for component in candidates[:2]:
                assignments[component] = spawn_group

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_batches += 1
            else:
                self._farmer_spawn_batches += 1
            return True

        # Build combat strength first; use later farm production to fund the
        # required farmer spawn without delaying the warrior batches.
        spawn_batch("warrior", 12)
        spawn_batch("warrior", 12)
        spawn_batch("farmer", 10)

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            c for c in components
            if self._role(c) == "warrior" and self._hp(c) > 0
        ]

        # Usually return one warrior at hunger 2 or 3, rotating the choice
        # so the group does not all leave together. Hunger 4 is the hard
        # safety limit: everyone at that point must head back.
        urgent = [c for c in warriors if self._hunger(c) >= 4]
        returning = list(urgent)

        if not urgent:
            eligible = [c for c in warriors if self._hunger(c) >= 2]
            if eligible:
                eligible.sort(
                    key=lambda c: (
                        self._hunger(c),
                        id(c),
                    ),
                    reverse=True,
                )
                returning = [eligible[self._return_cursor % len(eligible)]]
                self._return_cursor += 1

        returning_ids = {id(c) for c in returning}

        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif id(component) in returning_ids:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")