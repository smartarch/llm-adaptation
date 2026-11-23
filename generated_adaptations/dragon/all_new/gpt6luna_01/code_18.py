from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawned_extra_farmer = False

    @staticmethod
    def _role(villager):
        return str(getattr(villager, "role", "")).lower()

    @staticmethod
    def _since_meal(villager):
        return int(getattr(villager, "steps_since_meal", 0) or 0)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        farmers = list(getattr(environment, "farmers", []))
        warriors = list(getattr(environment, "warriors", []))
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)
        wheat = float(getattr(environment.farm, "wheat", 0) or 0)
        population = len(farmers) + len(warriors)

        # Eat at five steps without a meal, before starvation begins.
        hungry = [v for v in villagers if self._since_meal(v) >= 5]
        hungry_ids = {id(v) for v in hungry}
        for v in hungry:
            environment.assign_group(v, "eat")

        available = [v for v in villagers if id(v) not in hungry_ids]
        if dragon_hp <= 0:
            for v in available:
                environment.assign_group(v, "farm")
            return

        local_farmers = [v for v in available if self._role(v) == "farmer"]
        local_warriors = [v for v in available if self._role(v) == "warrior"]

        spawn_group = None
        spawn_pair = []

        # Prefer farmer pairs for spawning so Warriors remain available to fight.
        if len(local_farmers) >= 2:
            reserve = population
            warrior_count = len(warriors)

            # Build a larger attacking force before using a spawn on a Farmer.
            if warrior_count < 5 and wheat >= 12 + reserve:
                spawn_group = "spawn warrior"
            elif (
                not self._spawned_extra_farmer
                and warrior_count >= 5
                and wheat >= 10 + reserve
            ):
                spawn_group = "spawn farmer"
                self._spawned_extra_farmer = True
            elif wheat >= 12 + reserve:
                spawn_group = "spawn warrior"

            if spawn_group is not None:
                spawn_pair = local_farmers[:2]

        spawned_ids = {id(v) for v in spawn_pair}
        for v in spawn_pair:
            environment.assign_group(v, spawn_group)

        for v in available:
            if id(v) in spawned_ids:
                continue

            if self._role(v) == "farmer":
                environment.assign_group(v, "farm")
            elif self._since_meal(v) >= 4:
                environment.assign_group(v, "eat")
            else:
                environment.assign_group(v, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)

        for v in components:
            # Return at four steps without a meal so the villager can travel
            # back and eat before reaching the starvation threshold.
            if dragon_hp <= 0 or self._since_meal(v) >= 4:
                environment.assign_group(v, "village")
            else:
                environment.assign_group(v, "attack")