from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initial_farmer_count = None

    @staticmethod
    def _role(villager):
        return str(getattr(villager, "role", "")).lower()

    @staticmethod
    def _since_meal(villager):
        return int(getattr(villager, "steps_since_meal", 0) or 0)

    @staticmethod
    def _hp(villager):
        return float(getattr(villager, "hp", 0) or 0)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        farmers_all = list(getattr(environment, "farmers", []))
        warriors_all = list(getattr(environment, "warriors", []))

        if self._initial_farmer_count is None:
            self._initial_farmer_count = len(farmers_all)

        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)
        wheat = float(getattr(environment.farm, "wheat", 0) or 0)
        population = len(farmers_all) + len(warriors_all)
        warrior_count = len(warriors_all)

        # Feed before villagers reach six consecutive steps without a meal.
        hungry = [v for v in villagers if self._since_meal(v) >= 5]
        for v in hungry:
            environment.assign_group(v, "eat")

        available = [v for v in villagers if v not in hungry]
        farmers = [v for v in available if self._role(v) == "farmer"]

        # Keep food production going, but use a farmer pair to build the
        # Warrior force (or, once established, add a Farmer).
        spawn_group = None
        spawn_pair = []

        if dragon_hp > 0 and len(farmers) >= 2:
            meal_reserve = population
            can_afford_warrior = wheat >= 12 + meal_reserve
            can_afford_farmer = wheat >= 10 + meal_reserve

            if warrior_count < 6 and can_afford_warrior:
                spawn_group = "spawn warrior"
                spawn_pair = farmers[:2]
            elif (
                warrior_count >= 4
                and len(farmers_all) <= self._initial_farmer_count
                and can_afford_farmer
            ):
                spawn_group = "spawn farmer"
                spawn_pair = farmers[:2]

        for v in spawn_pair:
            environment.assign_group(v, spawn_group)

        spawned_ids = {id(v) for v in spawn_pair}

        # Farmers remain in the Village. A badly injured Warrior also stays
        # there rather than risking an immediate death in the Cave.
        for v in available:
            if id(v) in spawned_ids:
                continue
            if self._role(v) == "farmer":
                environment.assign_group(v, "farm")
            elif dragon_hp > 0 and self._hp(v) > 1:
                environment.assign_group(v, "cave")
            else:
                environment.assign_group(v, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)

        for v in components:
            # Return with enough time to travel and eat before starvation.
            if dragon_hp <= 0 or self._since_meal(v) >= 4 or self._hp(v) <= 1:
                environment.assign_group(v, "village")
            else:
                environment.assign_group(v, "attack")