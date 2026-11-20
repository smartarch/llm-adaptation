from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _meal_age(component):
        try:
            return max(0, int(component.steps_since_meal))
        except (AttributeError, TypeError, ValueError):
            return 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        assigned = set()

        def assign(i, group):
            environment.assign_group(components[i], group)
            assigned.add(i)

        try:
            wheat = max(0, int(environment.farm.wheat))
        except (AttributeError, TypeError, ValueError):
            wheat = 0

        # Feed before travel or spawning. Account for these meals when
        # deciding how much wheat can safely be spent on spawns.
        meals = []
        for i, component in enumerate(components):
            age = self._meal_age(component)
            if age >= 5 or (
                self._role(component) == "warrior" and age >= 3
            ):
                meals.append(i)

        for i in meals:
            assign(i, "eat")
        wheat = max(0, wheat - len(meals))

        def spawn_pair():
            candidates = [
                i for i, component in enumerate(components)
                if i not in assigned and self._meal_age(component) < 3
            ]
            # Use farmers first, so warriors already in the Village can
            # travel to the Cave and join the attack.
            candidates.sort(
                key=lambda i: self._role(components[i]) != "farmer"
            )
            return candidates[:2] if len(candidates) >= 2 else []

        # Build combat strength first; the Dragon must be killed within the
        # limited game duration, so do not stop at only two new warriors.
        while self._warrior_spawn_requests < 8 and wheat >= 12:
            pair = spawn_pair()
            if len(pair) != 2:
                break
            for i in pair:
                assign(i, "spawn warrior")
            wheat -= 12
            self._warrior_spawn_requests += 1

        # Also satisfy the farmer-spawn objective when resources and workers
        # permit, without displacing warrior spawning when wheat is scarce.
        if self._farmer_spawn_requests < 1 and wheat >= 10:
            pair = spawn_pair()
            if len(pair) == 2:
                for i in pair:
                    assign(i, "spawn farmer")
                wheat -= 10
                self._farmer_spawn_requests += 1

        # Assign every remaining villager explicitly. Warriors travel to
        # attack; farmers remain in the Village and produce food.
        for i, component in enumerate(components):
            if i in assigned:
                continue
            if self._role(component) == "warrior":
                assign(i, "cave")
            else:
                assign(i, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._role(component) != "warrior":
                environment.assign_group(component, "village")
            elif self._meal_age(component) >= 4:
                # Return early enough to reach the Village and eat before
                # starvation prevents the warrior from dealing damage.
                environment.assign_group(component, "village")
            else:
                environment.assign_group(component, "attack")