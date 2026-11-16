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
            if self._role(component) == "warrior":
                # Keep hungry warriors in the Village until they have eaten.
                assignments[component] = (
                    "farm" if self._hunger(component) >= 3 else "cave"
                )
            else:
                assignments[component] = "farm"

        # Meals take priority. At hunger 5, a villager must eat now to avoid
        # reaching the starvation threshold on the next step.
        meal_candidates = [
            c for c in components
            if self._hunger(c) >= 5
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

            candidates = [
                c for c in components
                if assignments[c] in ("farm", "cave")
            ]
            # Preserve warriors for combat when farmers are available.
            candidates.sort(
                key=lambda c: (
                    self._role(c) != "farmer",
                    -self._hunger(c),
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

        # Recruit warriors as soon as the wheat is available. Spawn one batch
        # per step so each action has a distinct pair of villagers.
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

        # Anyone at hunger 4 must return. Otherwise rotate a warrior at hunger
        # 2 or 3 back early, which leaves time to travel and eat safely.
        returning = {
            id(c) for c in warriors
            if self._hunger(c) >= 4
        }

        if not returning:
            eligible = [
                c for c in warriors
                if self._hunger(c) >= 2
            ]
            if eligible:
                eligible.sort(
                    key=lambda c: (
                        self._hunger(c),
                        self._hp(c),
                    ),
                    reverse=True,
                )
                returning.add(id(eligible[0]))

        for component in components:
            if self._role(component) != "warrior" or self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif id(component) in returning:
                self._assign(environment, component, "village")
            else:
                self._assign(environment, component, "attack")