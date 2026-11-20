from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_warriors = 0
        self._spawned_farmers = 0
        self._returning_meal_reserve = 0

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _hunger(component):
        return int(getattr(component, "steps_since_meal", 0))

    @staticmethod
    def _hp(component):
        return int(getattr(component, "hp", 1))

    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Default assignments keep farmers farming and send eligible warriors
        # toward the Cave. Every component is explicitly reassigned below.
        assignments = {}
        for component in components:
            if self._role(component) == "warrior":
                assignments[component] = (
                    "cave" if self._hunger(component) < 3 else "farm"
                )
            else:
                assignments[component] = "farm"

        wheat = max(0, int(getattr(environment.farm, "wheat", 0)))

        # Eat the most urgent villagers first. Warriors eat earlier because
        # they need time to travel back to the Cave after their meal.
        hungry = sorted(
            components,
            key=lambda c: (
                self._hunger(c) < (3 if self._role(c) == "warrior" else 4),
                -self._hunger(c),
            ),
        )
        for component in hungry:
            threshold = 3 if self._role(component) == "warrior" else 4
            if self._hunger(component) >= threshold and wheat > 0:
                assignments[component] = "eat"
                wheat -= 1

        # Keep food available for warriors returning from the Cave. The reserve
        # is advisory: urgent villagers above are fed first.
        reserve = min(wheat, self._returning_meal_reserve)

        def spawn_one(kind, cost):
            nonlocal wheat, reserve
            counter = (
                self._spawned_warriors
                if kind == "warrior"
                else self._spawned_farmers
            )
            target = 2 if kind == "warrior" else 1
            if counter >= target or wheat < cost + reserve:
                return

            # Use farmers first so warriors can get to the Cave. Do not take
            # villagers already assigned to eat out of the meal group.
            candidates = [
                c for c in components
                if assignments[c] != "eat"
            ]
            candidates.sort(
                key=lambda c: (self._role(c) != "farmer", self._hunger(c))
            )
            if len(candidates) < 2:
                return

            for component in candidates[:2]:
                assignments[component] = (
                    "spawn warrior" if kind == "warrior" else "spawn farmer"
                )

            wheat -= cost
            if kind == "warrior":
                self._spawned_warriors += 1
            else:
                self._spawned_farmers += 1

        # Prioritize warriors to build Dragon damage, then add a farmer.
        spawn_one("warrior", 12)
        reserve = min(wheat, self._returning_meal_reserve)
        spawn_one("farmer", 10)

        for component in components:
            self._assign(environment, component, assignments[component])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        returning = 0

        for component in components:
            if self._role(component) != "warrior":
                # Farmers belong in the Village; this also protects them from
                # Dragon attacks if one ever reaches the Cave.
                self._assign(environment, component, "village")
            elif self._hp(component) <= 0:
                self._assign(environment, component, "village")
            elif self._hunger(component) >= 4:
                # One step of travel followed by a Village meal keeps the
                # warrior from reaching the starvation threshold.
                self._assign(environment, component, "village")
                returning += 1
            else:
                self._assign(environment, component, "attack")

        self._returning_meal_reserve = returning