from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group name constants (must match exact strings)
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        # Warriors are kept in cave by default; we still classify for convenience
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors go to cave; Farmers stay in village farming by default
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Read current wheat
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Step 2: Compute safe Warrior spawns
        # We want to spawn Warriors only if we can leave at least 2 farmers to farm afterwards.
        num_farmers = len(farmers)
        if num_farmers >= 4 and wheat >= 12:
            # Maximum Warrior spawns we could attempt based on farmers and wheat
            max_warrior_spawns = min(num_farmers // 2, wheat // 12)
            # Ensure at least 2 farmers remain to farm after spawning warriors
            if num_farmers - 2 * max_warrior_spawns < 2:
                max_warrior_spawns = max(0, (num_farmers - 2) // 2)

            spawn_warriors_count = 2 * max_warrior_spawns
        else:
            spawn_warriors_count = 0

        if spawn_warriors_count > 0:
            # Move the first spawn_warriors_count farmers to the SPAWN_WARRIOR group
            for c in farmers[:spawn_warriors_count]:
                environment.assign_group(c, SPAWN_WARRIOR)

        # Step 3: Compute Farmer spawns after Warrior spawns
        remaining_farmers_after_war = num_farmers - spawn_warriors_count
        remaining_wheat_after_war = wheat - (spawn_warriors_count * 12)

        spawn_farmers_count = 0
        if remaining_farmers_after_war >= 2 and remaining_wheat_after_war >= 10:
            # Max Farmer spawns from remaining resources
            max_farmer_spawns = min(remaining_farmers_after_war // 2,
                                    remaining_wheat_after_war // 10)
            spawn_farmers_count = 2 * max_farmer_spawns

            # Move the next 2*max_farmer_spawns farmers to the SPAWN_FARMER group
            for c in farmers[spawn_warriors_count:
                             spawn_warriors_count + spawn_farmers_count]:
                environment.assign_group(c, SPAWN_FARMER)

        # Step 4: The rest of the farmers stay farming
        rest_start = spawn_warriors_count + spawn_farmers_count
        for c in farmers[rest_start:]:
            environment.assign_group(c, FARM)

        # Note:
        # - Warriors are already directed to the "cave" group by default.
        # - Spawn groups will create new villagers in subsequent steps per game rules.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group name constants
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors should attack
                environment.assign_group(c, ATTACK)
            else:
                # Farmers in the cave should go back to the village
                environment.assign_group(c, VILLAGE)

        # Note: If there are any Farmers in the Cave due to edge cases, they are moved to village.