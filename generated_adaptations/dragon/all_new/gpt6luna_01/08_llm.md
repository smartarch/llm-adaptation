I’d make Warrior trips predictable: send only recently fed Warriors to the Cave, let them attack until they need to return for food, and keep Farmers in the Village. Spawn Warriors whenever the wheat reserve allows, then spawn a Farmer after the Warrior force is established. This avoids cutting trips short while maintaining a reliable food supply.

```py
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

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        farmers = list(getattr(environment, "farmers", []))
        warriors = list(getattr(environment, "warriors", []))

        if self._initial_farmer_count is None:
            self._initial_farmer_count = len(farmers)

        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)
        wheat = float(getattr(environment.farm, "wheat", 0) or 0)
        population = len(farmers) + len(warriors)
        warrior_count = len(warriors)

        # Eat early enough that a villager can travel and still avoid starvation.
        hungry = [v for v in villagers if self._since_meal(v) >= 4]
        for v in hungry:
            environment.assign_group(v, "eat")

        available = [v for v in villagers if v not in hungry]
        local_farmers = [v for v in available if self._role(v) == "farmer"]

        # Spawn from farmer pairs when food permits, prioritizing Warriors.
        spawn_group = None
        spawn_pair = []
        meal_reserve = population

        if dragon_hp > 0 and len(local_farmers) >= 2:
            if warrior_count < 8 and wheat >= 12 + meal_reserve:
                spawn_group = "spawn warrior"
                spawn_pair = local_farmers[:2]
            elif (
                warrior_count >= 4
                and len(farmers) <= self._initial_farmer_count
                and wheat >= 10 + meal_reserve
            ):
                spawn_group = "spawn farmer"
                spawn_pair = local_farmers[:2]

        for v in spawn_pair:
            environment.assign_group(v, spawn_group)
        spawned = {id(v) for v in spawn_pair}

        for v in available:
            if id(v) in spawned:
                continue

            role = self._role(v)
            if role == "farmer":
                # Farmers remain safely in the Village and produce food.
                environment.assign_group(v, "farm")
            elif dragon_hp > 0:
                # A Warrior who has not eaten recently should eat before
                # beginning another trip to the Cave.
                if self._since_meal(v) >= 3:
                    environment.assign_group(v, "eat")
                else:
                    environment.assign_group(v, "cave")
            else:
                environment.assign_group(v, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = float(getattr(environment.dragon, "hp", 0) or 0)

        for v in components:
            # Stay and attack through the trip; return early enough to travel
            # back and eat before reaching six consecutive steps without food.
            if dragon_hp <= 0 or self._since_meal(v) >= 4:
                environment.assign_group(v, "village")
            else:
                environment.assign_group(v, "attack")
```