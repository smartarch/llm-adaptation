import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economy first, then continuous warrior production.
    - Warriors go to the Cave immediately and attack every step.
    - Three farmers always stay on the farm.
    - While fewer than 6 farmers exist, spare farmers are paired and spawn
      farmers (10 wheat). After that, spare farmers spawn warriors (12 wheat).
    - Farmers never enter the Cave.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    RESERVE_FARMERS = 3
    FARMER_TARGET = 6

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors head straight to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Reserve farmers that keep producing wheat.
        reserve = min(self.RESERVE_FARMERS, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_farmer = []
        spawn_warrior = []

        if len(farmers) < self.FARMER_TARGET:
            # Economy phase: grow the farmer population.
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST
        else:
            # Army phase: convert spare farmers into warriors.
            while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
                spawn_warrior.extend(available[:2])
                available = available[2:]
                wheat -= self.WARRIOR_SPAWN_COST

        # Anyone left over keeps farming.
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
                # Farmers never fight; send them back to the Village.
                environment.assign_group(c, "village")