from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_batches = 0
        self._farmer_spawn_batches = 0

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
                # Hungry warriors eat before they travel to the Cave.
                assignments[component] = "eat" if hunger >= 3 else "cave"
            else:
                assignments[component] = "farm"

        # Allocate each meal exactly once, and never allocate more meals than
        # the current wheat stock can pay for.
        meal_candidates = [
            c for c in components
            if self._hunger(c) >= (3 if self._role(c) == "warrior" else 4)
        ]
        meal_candidates.sort(
            key=lambda c: (
                self._hunger(c),
                self._role(c) == "warrior",
            ),
            reverse=True,
        )

        meals_assigned = set()
        for component in meal_candidates:
            if wheat <= 0:
                break
            assignments[component] = "eat"
            meals_assigned.add(component)
            wheat -= 1

        # Keep a reserve for villagers approaching meal time. This prevents
        # spawning from consuming the wheat needed to avoid starvation.
        approaching_meal = sum(
            1 for c in components
            if c not in meals_assigned and self._hunger(c) >= 2
        )
        reserve = max(3, approaching_meal)

        def spawn_batch(kind, cost):
            nonlocal wheat, reserve

            if kind == "warrior":
                if self._warrior_spawn_batches >= 2:
                    return False
                group = "spawn warrior"
            else:
                if self._farmer_spawn_batches >= 1:
                    return False
                group = "spawn farmer"

            if wheat < cost + reserve:
                return False

            candidates = [
                c for c in components
                if assignments[c] == "farm"
            ]
            candidates.sort(
                key=lambda c: (
                    self._role(c) != "farmer",
                    self._hunger(c),
                )
            )
            if len(candidates) < 2:
                return False

            # Prefer using farmers, but keep at least one farmer farming when
            # possible. If there is only one farmer, use other available
            # villagers for the pair instead.
            farmers = [c for c in candidates if self._role(c) == "farmer"]
            if len(farmers) >= 3:
                pair = farmers[:2]
            elif len(farmers) == 2 and len(candidates) > 2:
                pair = [farmers[0], next(c for c in candidates if c is not farmers[0])]
            else:
                pair = candidates[:2]

            for component in pair:
                assignments[component] = group

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_batches += 1
            else:
                self._farmer_spawn_batches += 1
            return True

        # Add Dragon damage first, then add a farmer once there is enough
        # wheat beyond the meal reserve.
        spawn_batch("warrior", 12)
        spawn_batch("farmer", 10)

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [
            c for c in components
            if self._role(c) == "warrior" and self._hp(c) > 0
        ]

        # Stagger meal trips. A warrior returns at hunger 3, leaving a step
        # to travel to the Village and eat before reaching the starvation limit.
        due = sorted(
            (c for c in warriors if self._hunger(c) >= 3),
            key=self._hunger,
            reverse=True,
        )

        returning = []
        if due:
            # Keep at least one warrior attacking when possible.
            returning = due[:1]
            if len(warriors) == 1 and self._hunger(warriors[0]) < 5:
                returning = []

        returning_ids = {id(c) for c in returning}

        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif id(component) in returning_ids:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")