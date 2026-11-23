The earlier spawn logic accidentally excluded one of two available Farmers, so it could fail to spawn even when wheat was sufficient. This version lets a pair of Farmers spawn a Warrior, prioritizes Warriors until the force is established, and then adds a Farmer. Warriors only start a Cave trip just after eating and return early enough to eat safely; Farmers stay in the Village to produce food.  
```py
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

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        farmers = list(getattr(environment, "farmers", []))
        warriors = list(getattr(environment, "warriors", []))
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)
        wheat = float(getattr(environment.farm, "wheat", 0) or 0)
        population = len(farmers) + len(warriors)

        # Keep a meal reserve for the whole population and feed early enough
        # to leave time for travel between the Village and the Cave.
        hungry = [v for v in villagers if self._since_meal(v) >= 3]
        for v in hungry:
            environment.assign_group(v, "eat")

        available = [v for v in villagers if v not in hungry]
        if dragon_hp <= 0:
            for v in available:
                environment.assign_group(v, "farm")
            return

        local_farmers = [v for v in available if self._role(v) == "farmer"]
        local_warriors = [v for v in available if self._role(v) == "warrior"]

        # Use a pair of villagers to spawn whenever the food cost plus one
        # meal per villager is available. Prefer farmer pairs so Warriors can
        # remain available to attack.
        candidates = local_farmers + local_warriors
        spawn_group = None
        if len(candidates) >= 2:
            reserve = population
            warrior_count = len(warriors)

            if warrior_count < 5 and wheat >= 12 + reserve:
                spawn_group = "spawn warrior"
            elif (
                warrior_count >= 5
                and not self._extra_farmer_spawned
                and wheat >= 10 + reserve
            ):
                spawn_group = "spawn farmer"
                self._extra_farmer_spawned = True
            elif wheat >= 12 + reserve:
                spawn_group = "spawn warrior"

        spawned = set()
        if spawn_group is not None:
            for v in candidates[:2]:
                environment.assign_group(v, spawn_group)
                spawned.add(id(v))

        for v in available:
            if id(v) in spawned:
                continue

            if self._role(v) == "farmer":
                environment.assign_group(v, "farm")
            elif self._since_meal(v) <= 1:
                # Only begin a Cave trip just after eating, so there is time
                # for multiple attacks before returning for the next meal.
                environment.assign_group(v, "cave")
            else:
                environment.assign_group(v, "eat")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)

        for v in components:
            # A returning villager travels to the Village and can eat on the
            # next assignment, before starvation becomes a risk.
            if dragon_hp <= 0 or self._since_meal(v) >= 3:
                environment.assign_group(v, "village")
            else:
                environment.assign_group(v, "attack")
```