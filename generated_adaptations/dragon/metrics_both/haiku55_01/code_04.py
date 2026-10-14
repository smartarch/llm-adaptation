from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - All warriors go to the Cave to attack.
      - Farmers: spawn a Warrior whenever the farm has 12+ wheat and two
        farmers are available (warriors give the most damage). Spawn a Farmer
        (10 wheat) while the farmer count is below 4 to strengthen wheat income.
        All remaining farmers keep farming.
    Cave:
      - Warriors attack the Dragon every step.
      - Any farmer in the Cave is sent back to the Village.
    """

    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12
    TARGET_FARMERS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior goes to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        remaining = list(farmers)
        farmer_count = len(farmers)

        # Prefer growing the farmer economy early, then spend wheat on warriors.
        if (len(remaining) >= 2
                and farmer_count < self.TARGET_FARMERS
                and wheat >= self.FARMER_SPAWN_COST):
            for f in remaining[:2]:
                environment.assign_group(f, "spawn farmer")
            remaining = remaining[2:]
            wheat -= self.FARMER_SPAWN_COST
        elif len(remaining) >= 2 and wheat >= self.WARRIOR_SPAWN_COST:
            for f in remaining[:2]:
                environment.assign_group(f, "spawn warrior")
            remaining = remaining[2:]
            wheat -= self.WARRIOR_SPAWN_COST

        # Everyone else keeps farming to produce wheat.
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers must not stay in the Cave.
                environment.assign_group(c, "village")