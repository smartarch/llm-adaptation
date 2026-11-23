from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._extra_farmer_spawned = False

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
        all_farmers = list(getattr(environment, "farmers", []))
        all_warriors = list(getattr(environment, "warriors", []))
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)
        wheat = float(getattr(environment.farm, "wheat", 0) or 0)

        population = len(all_farmers) + len(all_warriors)
        warrior_count = len(all_warriors)

        # Feed before villagers get close to the six-step starvation limit.
        hungry = [v for v in villagers if self._since_meal(v) >= 4]
        for v in hungry:
            environment.assign_group(v, "eat")

        available = [v for v in villagers if v not in hungry]
        local_farmers = [v for v in available if self._role(v) == "farmer"]
        local_warriors = [v for v in available if self._role(v) == "warrior"]

        if dragon_hp <= 0:
            for v in available:
                environment.assign_group(v, "farm")
            return

        # Keep at least one Farmer working when possible. Use other available
        # villagers for spawning, preferring Farmers so Warriors can attack.
        spawn_candidates = []
        spawn_candidates.extend(local_farmers[:-1] if len(local_farmers) > 1 else [])
        if len(spawn_candidates) < 2:
            spawn_candidates.extend(local_warriors)

        spawn_group = None
        if len(spawn_candidates) >= 2:
            meal_reserve = population

            # Add a Farmer once the Warrior force is established, then focus
            # on continually building the damage-dealing force.
            if (
                not self._extra_farmer_spawned
                and warrior_count >= 4
                and wheat >= 10 + meal_reserve
            ):
                spawn_group = "spawn farmer"
                self._extra_farmer_spawned = True
            elif wheat >= 12 + meal_reserve:
                spawn_group = "spawn warrior"

        spawned = set()
        if spawn_group is not None:
            for v in spawn_candidates[:2]:
                environment.assign_group(v, spawn_group)
                spawned.add(id(v))

        for v in available:
            if id(v) in spawned:
                continue

            if self._role(v) == "farmer":
                environment.assign_group(v, "farm")
            elif self._since_meal(v) >= 3:
                environment.assign_group(v, "eat")
            elif self._hp(v) > 1:
                environment.assign_group(v, "cave")
            else:
                environment.assign_group(v, "eat")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)

        for v in components:
            # A Warrior returns early enough to travel to the Village and eat,
            # but otherwise keeps attacking to prevent Dragon regeneration.
            if dragon_hp <= 0 or self._since_meal(v) >= 4 or self._hp(v) <= 1:
                environment.assign_group(v, "village")
            else:
                environment.assign_group(v, "attack")