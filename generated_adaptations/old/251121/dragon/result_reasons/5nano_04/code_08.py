from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Aggressive spawning with correct wheat budgeting.
        # - Move all Warriors to the Cave (they will attack once there).
        # - Keep Farmers farming (in the village) and use wheat to spawn more Farmers and Warriors.
        if not components:
            return

        # Classify villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the cave (towards the Dragon)
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Keep Farmers in the Village (farming)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Aggressive, budgeted spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmer spawns: need 2 farmers and 10 wheat per spawn
        n_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Trigger farmer spawns
        for i in range(n_farm_spawns):
            c1 = farmers[2 * i]
            c2 = farmers[2 * i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")

        # Update wheat budget after farmer spawns
        wheat_after_farm = wheat - n_farm_spawns * 10
        idx_after_farm = 2 * n_farm_spawns

        remaining_farmers_for_war = len(farmers) - idx_after_farm

        # Warrior spawns: need 2 farmers and 12 wheat per spawn
        n_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)

        # Trigger warrior spawns
        for i in range(n_war_spawns):
            c1 = farmers[idx_after_farm + 2 * i]
            c2 = farmers[idx_after_farm + 2 * i + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - All Warriors should attack (group "attack").
        # - All Farmers should go back to the Village (group "village").
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")