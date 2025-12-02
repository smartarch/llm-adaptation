from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - "farm": Farmers stay in Village to farm
        - "cave": Warriors go to the Cave
        Spawn groups ("spawn farmer", "spawn warrior") are not used in this basic strategy.
        """
        for comp in components:
            # Warriors go to the Cave
            if getattr(comp, "role", None) == "Warrior":
                environment.assign_group(comp, "cave")
            # Farmers stay in the Village to farm
            else:
                environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - "attack": Warriors attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village
        The strategy keeps Farmers in the Village; Warriors attack in the cave.
        """
        for comp in components:
            if getattr(comp, "role", None) == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                environment.assign_group(comp, "village")