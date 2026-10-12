from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather current villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Ensure all existing Warriors move to the Cave to start attacking
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning among Farmers
        # Current wheat available in the Farm
        wheat = 0
        if hasattr(environment, "farm") and environment.farm is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Determine Warrior spawns first:
        # Each Warrior spawn requires 2 Farmers (spawners) and 12 wheat.
        max_warrior_spawns = min(len(farmers) // 2, wheat // 12)

        # Reserve Farmers used for Warrior spawns
        spawner_for_warriors = 2 * max_warrior_spawns
        remaining_farmers = len(farmers) - spawner_for_warriors

        # Wheat left after Warrior spawns
        wheat_after_warrior_spawns = max(0, wheat - max_warrior_spawns * 12)

        # Determine Farmer spawns with remaining wheat
        max_farmer_spawns = min(remaining_farmers // 2, wheat_after_warrior_spawns // 10)
        spawner_for_farmers = 2 * max_farmer_spawns

        # 3) Assign groups for Farmers
        # Order: first spawner_for_warriors -> "spawn warrior",
        # then spawner_for_farmers -> "spawn farmer",
        # rest -> "farm"
        total_farmers = len(farmers)

        for i, c in enumerate(farmers):
            if i < spawner_for_warriors:
                environment.assign_group(c, "spawn warrior")
            elif i < spawner_for_warriors + spawner_for_farmers:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")

        # Note: Warriors have already been moved to the cave above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, map roles to actions
        for c in components:
            role = getattr(c, "role", None)

            if role == "Warrior":
                # Attack the Dragon
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Return Farmers to Village
                environment.assign_group(c, "village")
            else:
                # Fallback: stay in cave
                environment.assign_group(c, "cave")