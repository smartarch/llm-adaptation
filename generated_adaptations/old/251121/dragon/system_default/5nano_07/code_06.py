from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - "cave": send Warriors to the Cave (to attack)
        - "spawn warrior": spawn a new Warrior (requires 2 Farmers and 12 wheat)
        - "spawn farmer": spawn a new Farmer (requires 2 Farmers and 10 wheat)
        - "farm": remaining Farmers continue farming

        Strategy (SW-first):
        - Compute how many Spawn Warrior events we can support: SW = min(F//2, W//12)
        - Subtract used wheat for SW
        - Compute how many Spawn Farmer events we can support with remaining Farmers and Wheat: SF = min((F - 2*SW)//2, (W - 12*SW)//10)
        - Assign: first 2*SW Farmers to "spawn warrior"
        - Next 2*SF Farmers to "spawn farmer"
        - Remaining Farmers to "farm"
        - All Warriors go to the Cave
        """
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Warriors go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Spawn logic for farmers (prioritize Warriors)
        F = len(farmers)
        W = getattr(environment.farm, "wheat", 0)

        # Spawn Warriors first
        SW = min(F // 2, W // 12)
        W_after_SW = W - SW * 12

        # Then Spawn Farmers with remaining wheat
        SF = min((F - 2 * SW) // 2, W_after_SW // 10)

        # Assign farmers to groups
        idx = 0
        # Spawn Warriors: 2 farmers per SW
        for _ in range(2 * SW):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        # Spawn Farmers: 2 farmers per SF
        for _ in range(2 * SF):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        # Remaining farmers go to farming
        for _ in range(F - idx):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Cave:
        - Warriors -> "attack" (attack the Dragon)
        - Farmers  -> "village" (return to Village)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")