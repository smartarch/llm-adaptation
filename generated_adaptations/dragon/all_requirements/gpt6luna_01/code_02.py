from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._planned_farmer_spawns = 0
        self._planned_warrior_spawns = 0

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _meal_age(component):
        try:
            return int(component.steps_since_meal)
        except (AttributeError, TypeError, ValueError):
            return 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        assigned = set()

        def assign(index, group):
            environment.assign_group(components[index], group)
            assigned.add(index)

        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)
        try:
            wheat = max(0, int(wheat))
        except (TypeError, ValueError):
            wheat = 0

        # Eat before spawning or leaving for the Cave. Warriors eat at age 3
        # so that they do not set out too hungry; everyone eats by age 5.
        for i, component in enumerate(components):
            age = self._meal_age(component)
            role = self._role(component)
            if age >= 5 or (role == "warrior" and age >= 3):
                assign(i, "eat")

        # Spawn targets are tracked so the same target is not repeatedly
        # requested. Each spawn group needs a pair and its full wheat cost.
        def choose_pair():
            candidates = [
                i for i, c in enumerate(components)
                if i not in assigned and self._meal_age(c) < 3
            ]
            # Prefer farmers as spawn workers, preserving warriors for combat.
            candidates.sort(key=lambda i: self._role(components[i]) != "farmer")
            return candidates[:2] if len(candidates) >= 2 else []

        if self._planned_farmer_spawns < 1 and wheat >= 10:
            pair = choose_pair()
            if len(pair) == 2:
                for i in pair:
                    assign(i, "spawn farmer")
                wheat -= 10
                self._planned_farmer_spawns += 1

        while self._planned_warrior_spawns < 2 and wheat >= 12:
            pair = choose_pair()
            if len(pair) != 2:
                break
            for i in pair:
                assign(i, "spawn warrior")
            wheat -= 12
            self._planned_warrior_spawns += 1

        # Farmers stay in the Village. Warriors not eating or spawning travel
        # to the Cave, where they can attack on the following step.
        for i, component in enumerate(components):
            if i in assigned:
                continue
            if self._role(component) == "warrior":
                assign(i, "cave")
            else:
                assign(i, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            role = self._role(component)
            age = self._meal_age(component)

            # Farmers belong in the Village. Warriors return early enough to
            # travel back and eat before starvation makes them unable to fight.
            if role != "warrior" or age >= 4:
                environment.assign_group(component, "village")
            else:
                environment.assign_group(component, "attack")