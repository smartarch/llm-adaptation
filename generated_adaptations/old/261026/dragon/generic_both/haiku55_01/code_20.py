import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Adaptive-reserve strategy with immediate warrior attacks.
    - Warriors go to the Cave and attack every step.
    - Farmers never enter the Cave. The number kept farming adapts to the
      current farmer count, with a floor of one.
    - If fewer than 3 farmers exist, spare pairs spawn farmers (10 wheat).
    - Otherwise spare pairs spawn warriors (12 wheat) while wheat allows.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    MIN_FARMERS = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        for w in warriors:
            environment.assign_group(w, "cave")

        n = len(farmers)
        # Adaptive reserve: about one farmer in three keeps farming, floor of one.
        reserve = min(n, max(1, n // 3))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_farmer = []
        spawn_warrior = []

        if n < self.MIN_FARMERS:
            # Rebuild the wheat economy first.
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST
        else:
            # Convert spare farmers into warriors while wheat allows.
            while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
                spawn_warrior.extend(available[:2])
                available = available[2:]
                wheat -= self.WARRIOR_SPAWN_COST

        farming.extend(available)

        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in farming:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")