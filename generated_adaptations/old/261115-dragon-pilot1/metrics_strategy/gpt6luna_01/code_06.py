from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Counts successful spawn requests (each request assigns a pair).
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _assign(environment, component, group, group_ids):
        if group not in group_ids:
            raise ValueError(f"Required group {group!r} is not available")
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        meals_due = 0

        for component in components:
            if component.role == "Warrior":
                # Eat in the Village before returning to the Cave.
                if component.steps_since_meal >= 4:
                    self._assign(environment, component, "eat", group_ids)
                    meals_due += 1
                else:
                    self._assign(environment, component, "cave", group_ids)
            elif component.steps_since_meal >= 5:
                self._assign(environment, component, "eat", group_ids)
                meals_due += 1
            else:
                farmers.append(component)

        # Keep enough wheat for meals and a small reserve.
        wheat_available = max(0, environment.farm.wheat - meals_due - 3)

        # Spawn Warriors first, since they contribute directly to damage.
        spawn_plan = []
        if self._warrior_spawn_requests < 2:
            spawn_plan.append(("spawn warrior", 12, "warrior"))
        if self._farmer_spawn_requests < 2:
            spawn_plan.append(("spawn farmer", 10, "farmer"))

        for group, cost, role in spawn_plan:
            if len(farmers) < 2 or wheat_available < cost:
                continue

            pair = farmers[:2]
            farmers = farmers[2:]
            for component in pair:
                self._assign(environment, component, group, group_ids)

            wheat_available -= cost
            if role == "warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

        for component in farmers:
            self._assign(environment, component, "farm", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for component in components:
            if component.role != "Warrior":
                self._assign(environment, component, "village", group_ids)
            else:
                warriors.append(component)

        # Return Warriors before they become too hungry to fight. At the
        # threshold, send the most hungry one first to stagger meal trips.
        returning = [c for c in warriors if c.steps_since_meal >= 4]
        returning.sort(key=lambda c: c.steps_since_meal, reverse=True)

        # If anyone is close to starvation, get all such Warriors moving back.
        urgent = [c for c in returning if c.steps_since_meal >= 5]
        if urgent:
            return_set = set(urgent)
        else:
            return_set = set(returning[:1])

        for component in warriors:
            if component in return_set:
                self._assign(environment, component, "village", group_ids)
            else:
                self._assign(environment, component, "attack", group_ids)