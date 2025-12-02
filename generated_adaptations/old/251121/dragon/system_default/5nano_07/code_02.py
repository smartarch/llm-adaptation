from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - "cave": for Warriors to go to the Cave
        - "farm" or "spawn farmer": for Farmers to farm or spawn new farmers
        Spawn strategy:
        - Use available wheat on the Farm to determine how many new Farmers can be spawned:
          s = min(number_of_farmers_in_village // 2, farm.wheat // 10)
        - Assign 2*s Farmers to "spawn farmer" (to spawn s new Farmers)
        - Assign the remaining Farmers to "farm"
        Warriors are assigned to "cave" (they will go to the Cave)
        """
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Warriors go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Spawn farmer logic
        available_wheat = getattr(environment.farm, "wheat", 0)
        n_farmers = len(farmers)
        # Number of new farmers that can be spawned this step
        s = min(n_farmers // 2, available_wheat // 10)

        # 3) Assign farmers to either spawn farmer or farm
        # First 2*s farmers go to "spawn farmer" group, rest go to "farm"
        for idx, c in enumerate(farmers):
            if idx < 2 * s:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Cave:
        - Warriors -> "attack" (Attack the Dragon)
        - Farmers  -> "village" (Go back to Village)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")