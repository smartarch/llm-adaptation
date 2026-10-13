from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _is_warrior(component):
        return "warrior" in str(getattr(component, "role", "")).lower()

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []

        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)
                environment.assign_group(component, "farm")

        if len(farmers) < 2 or getattr(environment.dragon, "hp", 1) <= 0:
            return

        wheat = max(0, getattr(environment.farm, "wheat", 0))
        available_pairs = len(farmers) // 2
        assigned_pairs = 0

        # Prioritize early combat strength, then meet the Farmer spawn goal.
        # Track only batches actually assigned, and account for each batch's
        # wheat cost so the same reserve is not spent multiple times.
        while assigned_pairs < available_pairs:
            if self._warrior_spawn_requests < 2:
                spawn_group, cost = "spawn warrior", 12
            elif self._farmer_spawn_requests < 2:
                spawn_group, cost = "spawn farmer", 10
            else:
                # Keep at least one pair farming once the minimum spawn goals
                # have been met; spend remaining wheat on combat units.
                if available_pairs - assigned_pairs <= 1:
                    break
                spawn_group, cost = "spawn warrior", 12

            if wheat < cost:
                break

            first = assigned_pairs * 2
            environment.assign_group(farmers[first], spawn_group)
            environment.assign_group(farmers[first + 1], spawn_group)

            wheat -= cost
            assigned_pairs += 1

            if spawn_group == "spawn warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if self._is_warrior(component):
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")