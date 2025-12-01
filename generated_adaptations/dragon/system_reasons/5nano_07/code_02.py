from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village to farm wheat
        - cave: go to the Cave (for Warriors)
        - spawn farmer: for every 2 villagers in this group and 10 wheat, spawn a Farmer
        - spawn warrior: for every 2 villagers in this group and 12 wheat, spawn a Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors should move to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village, but we may use some to spawn
        # Current wheat available for spawning
        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Determine how many spawns we can trigger
        # Each spawn farmer uses 2 farmers and 10 wheat -> one new Farmer
        max_farm_spawns = len(farmers) // 2
        kf = min(max_farm_spawns, available_wheat // 10)

        # Wheat remaining after spawning farmers
        remaining_wheat = available_wheat - (kf * 10)

        # Each spawn warrior uses 2 farmers and 12 wheat -> one new Warrior
        max_war_spawns = (len(farmers) - 2 * kf) // 2
        kw = min(max_war_spawns, remaining_wheat // 12)

        # Allocate farmers to groups
        idx = 0

        # Assign 2*kf farmers to "spawn farmer"
        for _ in range(2 * kf):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign 2*kw farmers to "spawn warrior"
        for _ in range(2 * kw):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to "farm" (stay in Village and farm)
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Note: If there are no farmers, nothing else to do here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors should attack the Dragon
        - cave: stay in the Cave (if any non-Warrior ends up here, keep them here)
        - village: go back to Village (Farmers should return to Village)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in Village
                environment.assign_group(c, "village")