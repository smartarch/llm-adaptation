from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - "cave": for Warriors to go to the Cave
        - "farm" / "spawn farmer" / "spawn warrior": Farmers stay or spawn new villagers
        Spawn strategy:
        - Use available wheat on the Farm to determine how many spawn events we can support.
        - SF = number of spawn-farmer events: 2 farmers + 10 wheat -> 1 new farmer
        - SW = number of spawn-warrior events: 2 farmers + 12 wheat -> 1 new warrior
        - Allocate farmers into three groups disjointly: spawn farmer, spawn warrior, farm
        Warriors go to the cave; Farmers are allocated to one of the three farmer-related groups.
        """
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Warriors go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Spawn logic for farmers
        F = len(farmers)
        W = getattr(environment.farm, "wheat", 0)

        # Compute how many spawn-farmer events we can support
        SF = min(F // 2, W // 10)

        # Wheat remaining after spawn-farmer events
        W_after_SF = W - SF * 10

        # Compute how many spawn-warrior events we can support with remaining farmers and wheat
        SW = min((F - 2 * SF) // 2, W_after_SF // 12)

        # Final remaining wheat (not strictly needed, but kept for robustness)
        _W_final = W_after_SF - SW * 12

        # Assign farmers to groups
        # First 2*SF to "spawn farmer"
        # Next 2*SW to "spawn warrior"
        # Rest to "farm"
        idx = 0
        # spawn farmer
        for _ in range(2 * SF):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        # spawn warrior
        for _ in range(2 * SW):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        # remaining to farm
        for _ in range(F - idx):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

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