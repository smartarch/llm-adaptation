import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Aggressive warrior-focused strategy.
    - All warriors go to the Cave and attack the Dragon every step.
    - Farmers stay on the farm, except that as many pairs as wheat allows are
      sent to 'spawn warrior' to maximise the damage output quickly.
    - A farmer pair is spawned when the farmer population gets too low.
    - Any farmer that ends up in the Cave is sent back to the Village.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    LOW_FARMER_THRESHOLD = 4   # rebuild farmers if we drop below this
    MIN_FARMERS_FARMING = 2    # keep some wheat income

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the Cave to fight.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Reserve farmers that keep farming for wheat income.
        reserve = self.MIN_FARMERS_FARMING if len(farmers) >= 4 else 1
        reserve = min(reserve, len(farmers))
        farming = farmers[:reserve]
        available = farmers[reserve:]

        spawn_warrior = []
        spawn_farmer = []

        # Prefer warriors: consume wheat in pairs while possible.
        while len(available) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
            spawn_warrior.extend(available[:2])
            available = available[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # If the farmer population is low, rebuild it with leftover pairs.
        if len(farmers) < self.LOW_FARMER_THRESHOLD:
            while len(available) >= 2 and wheat >= self.FARMER_SPAWN_COST:
                spawn_farmer.extend(available[:2])
                available = available[2:]
                wheat -= self.FARMER_SPAWN_COST

        # Anyone left over keeps farming.
        farming.extend(available)

        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in farming:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers do not fight; send them back to the Village.
                environment.assign_group(c, "village")