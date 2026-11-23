from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_spawn_step = -10**9

    @staticmethod
    def _role(component):
        return str(getattr(component, "role", "")).lower()

    @staticmethod
    def _since_meal(component):
        return int(getattr(component, "steps_since_meal", 0) or 0)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = float(getattr(environment.farm, "wheat", 0) or 0)
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)

        # Feed villagers before they reach six consecutive steps without a meal.
        urgent = [v for v in villagers if self._since_meal(v) >= 5]
        for v in urgent:
            environment.assign_group(v, "eat")

        available = [v for v in villagers if v not in urgent]
        farmers = [v for v in available if self._role(v) == "farmer"]
        warriors = [v for v in available if self._role(v) == "warrior"]

        # Keep farmers working unless there is a large surplus of food and farmers.
        farmers_to_send = 0
        if wheat >= 8 and len(farmers) > 2:
            farmers_to_send = len(farmers) - 2
        elif wheat >= 20 and len(farmers) > 1:
            farmers_to_send = len(farmers) - 1

        for v in farmers[farmers_to_send:]:
            environment.assign_group(v, "farm")

        # Send healthy warriors to the Cave whenever the Dragon is still alive.
        for v in warriors:
            environment.assign_group(v, "cave" if dragon_hp > 0 else "farm")

        for v in farmers[:farmers_to_send]:
            environment.assign_group(v, "cave" if dragon_hp > 0 else "farm")

        # Spawn at most one warrior per cooldown period, and only with a food reserve.
        # Prefer to use warriors that would otherwise travel to the Cave.
        spawn_candidates = list(warriors)
        reserve = max(4, min(12, 2 * len(villagers)))
        can_spawn = (
            dragon_hp > 0
            and len(spawn_candidates) >= 2
            and wheat >= 12 + reserve
            and step - self._last_spawn_step >= 2
        )
        if can_spawn:
            for v in spawn_candidates[:2]:
                environment.assign_group(v, "spawn warrior")
            self._last_spawn_step = step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)

        for v in components:
            # Return early enough to travel to the Village and eat before starvation.
            if self._since_meal(v) >= 4 or dragon_hp <= 0:
                environment.assign_group(v, "village")
            else:
                environment.assign_group(v, "attack")