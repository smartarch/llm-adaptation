from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_batches = 0
        self._farmer_spawn_batches = 0
        self._returning = set()
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
            key = id(component)
            hunger = self._hunger(component)

            # Keep a returning warrior in the Village until they have eaten.
            if key in self._returning and hunger == 0:
                self._returning.discard(key)

            if self._role(component) == "warrior":
                if step >= 30:
                    assignments[component] = "cave"
                elif key in self._returning:
                    assignments[component] = "farm"
                else:
                    assignments[component] = "cave"
            else:
                assignments[component] = "farm"

        # Feed the hungriest villagers first, without assigning meals that
        # cannot be paid for.
        meal_candidates = sorted(
            (
                c for c in components
                if self._hunger(c) >= (
                    4 if self._role(c) == "warrior" else 5
                )
            ),
            key=lambda c: (
                self._hunger(c),
                self._role(c) == "warrior",
            ),
            reverse=True,
        )

        for component in meal_candidates:
            if wheat <= 0:
                break
            assignments[component] = "eat"
            wheat -= 1

        # Spawn batches only when both the wheat and two available villagers
        # remain after meal assignments. One batch per call avoids reusing a
        # villager in multiple spawn groups during the same step.
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

            candidates = [
                c for c in components
                if assignments[c] in ("farm", "cave")
                and self._hunger(c) < 4
                and id(c) not in self._returning
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

        if self._warrior_spawn_batches < 2:
            spawn_batch("warrior", 12)
        elif self._farmer_spawn_batches < 1:
            spawn_batch("farmer", 10)

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            c for c in components
            if self._role(c) == "warrior" and self._hp(c) > 0
        ]

        # At hunger 4, return to the Village so there is time to eat before
        # starvation. Below that, stagger earlier meal trips where possible.
        returning = {
            id(c) for c in warriors
            if self._hunger(c) >= 4
        }

        if not returning:
            eligible = [
                c for c in warriors
                if self._hunger(c) >= 3
            ]
            if eligible:
                eligible.sort(
                    key=lambda c: (
                        self._hunger(c),
                        self._hp(c),
                    ),
                    reverse=True,
                )
                returning.add(id(eligible[self._return_cursor % len(eligible)]))
                self._return_cursor += 1

        for component in components:
            key = id(component)
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif key in returning:
                self._returning.add(key)
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")