import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strictly rule-compliant, damage-focused strategy.
    - All warriors go to the Cave immediately and attack every step.
    - Farmers never enter the Cave. Two farmers always keep farming for wheat.
    - Remaining farmers are paired and spawn warriors whenever wheat allows.
    - If the farmer population falls below 4, pairs spawn farmers instead
      to rebuild the wheat economy.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    MIN_FARMING = 2
    MIN_FARMERS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors head straight to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Always keep a minimal farming core.
        reserve = min(self.MIN_FARMING, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        # Rebuild the farmer economy if too few farmers remain.
        if len(farmers) < self.MIN_FARMERS:
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST

        # Convert the remaining farmers into warriors while wheat allows.
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