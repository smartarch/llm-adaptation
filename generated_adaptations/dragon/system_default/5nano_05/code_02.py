from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        num_farmers = len(farmers)
        num_warriors = len(warriors)

        # Wheat available in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Compute possible spawns given current wheat and available farmers
        # Each Farmer spawn uses 2 villagers and 10 wheat -> spawns_farmer
        spawns_farmer = min(num_farmers // 2, wheat // 10)
        spawn_farmer_villagers = spawns_farmer * 2

        remaining_farmers = num_farmers - spawn_farmer_villagers
        remaining_wheat_after_farmer_spawns = wheat - (spawns_farmer * 10)  # wheat consumed by farmer spawns

        # Compute possible Warrior spawns with remaining resources
        spawns_warrior = min(remaining_farmers // 2, remaining_wheat_after_farmer_spawns // 12)
        spawn_warrior_villagers = spawns_warrior * 2

        # Remaining farmers to send to farming
        farm_villagers = remaining_farmers - spawn_warrior_villagers

        # Assign Warriors to cave (they should attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Assign Farmers to groups
        # First, assign to spawn farmer group
        for i in range(spawn_farmer_villagers):
            environment.assign_group(farmers[i], "spawn farmer")

        # Next, assign to spawn warrior group
        idx = spawn_farmer_villagers
        for i in range(spawn_warrior_villagers):
            environment.assign_group(farmers[idx + i], "spawn warrior")

        # Remaining farmers go to farm
        idx2 = idx + spawn_warrior_villagers
        for i in range(farm_villagers):
            environment.assign_group(farmers[idx2 + i], "farm")

        # Note: If there are any farmers left unassigned due to edge cases, place them in "farm" as a fallback
        remaining = num_farmers - (spawn_farmer_villagers + spawn_warrior_villagers + farm_villagers)
        if remaining > 0:
            for i in range(remaining):
                environment.assign_group(farmers[idx2 + farm_villagers + i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack the Dragon; Farmers should return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep safe assignment to village
                environment.assign_group(c, "village")