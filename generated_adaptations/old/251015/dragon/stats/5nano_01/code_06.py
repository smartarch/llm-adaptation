from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group name constants
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors go to cave; Farmers stay in farm by default
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Read current wheat
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Step 2: Spawn farmers if possible
        # Each new farmer requires 2 farmers in the spawn group and 10 wheat
        num_farmers = len(farmers)
        spawn_farmers_pairs = min(num_farmers // 2, wheat // 10)
        spawn_farmers_count = 2 * spawn_farmers_pairs

        # Move the first 2*spawn_farmers_pairs farmers to the spawn farmer group
        if spawn_farmers_count > 0:
            for c in farmers[:spawn_farmers_count]:
                environment.assign_group(c, SPAWN_FARMER)

        # After accounting for farmer spawns, determine remaining wheat
        remaining_wheat_after_farmers = wheat - (spawn_farmers_pairs * 10)

        # Step 3: Spawn warriors if possible from remaining farmers
        remaining_farmers = farmers[spawn_farmers_count:]
        warrior_spawns = min(len(remaining_farmers) // 2, remaining_wheat_after_farmers // 12)
        spawn_warriors_count = 2 * warrior_spawns

        if spawn_warriors_count > 0:
            for c in remaining_farmers[:spawn_warriors_count]:
                environment.assign_group(c, SPAWN_WARRIOR)

        # The rest of the farmers (not assigned to spawn groups) stay farming
        rest_start = spawn_farmers_count + spawn_warriors_count
        for c in farmers[rest_start:]:
            environment.assign_group(c, FARM)

        # Note: Warriors are already assigned to CAVE by default; no extra action needed here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group name constants
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors in cave should attack
                environment.assign_group(c, ATTACK)
            else:
                # Farmers in cave should return to the village
                environment.assign_group(c, VILLAGE)