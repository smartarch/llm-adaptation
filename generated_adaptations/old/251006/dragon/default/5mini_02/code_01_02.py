from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    """
    Adaptation strategy:
    - In the cave:
        * All Warriors -> "attack"
        * All Farmers -> "village" (send back)
    - In the village:
        * All Warriors -> "cave"
        * Farmers: keep one farming if possible; with remaining farmers form pairs to spawn warriors first
          (cost 12 wheat, 2 villagers per spawn), then spawn farmers if wheat & pairs remain (cost 10 wheat).
        * Remaining farmers -> "farm"
    """
    def assign_in_village(self, components, environment, group_ids, step: int):
        # Valid village group_ids: "farm", "cave", "spawn farmer", "spawn warrior"
        villagers = list(components)
        # Separate roles
        warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in villagers if getattr(c, "role", None) == "Farmer"]

        # 1) Send all warriors in village to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # If no farmers, nothing to do for farming/spawning
        if not farmers:
            return

        # Reserve one farmer to always farm (to maintain wheat income) if possible
        # Deterministic: pick the first as the reserved farmer
        reserved = farmers[0]
        others = farmers[1:]  # available for spawn or farm

        wheat = int(getattr(environment.farm, "wheat", 0))

        # Determine how many warrior spawns we can afford (each needs 2 villagers and 12 wheat)
        max_pairs_available = len(others) // 2
        max_warrior_spawns_by_wheat = wheat // 12
        warrior_spawns = min(max_pairs_available, max_warrior_spawns_by_wheat)

        # Allocate villagers to spawn warrior
        num_farmers_for_wspawn = warrior_spawns * 2
        spawn_warrior_group = others[:num_farmers_for_wspawn]
        remaining_after_wspawn = others[num_farmers_for_wspawn:]

        wheat_after_wspawn = wheat - warrior_spawns * 12

        # Determine how many farmer spawns we can afford (each needs 2 villagers and 10 wheat)
        max_pairs_remaining = len(remaining_after_wspawn) // 2
        max_farmer_spawns_by_wheat = wheat_after_wspawn // 10
        farmer_spawns = min(max_pairs_remaining, max_farmer_spawns_by_wheat)

        num_farmers_for_fspawn = farmer_spawns * 2
        spawn_farmer_group = remaining_after_wspawn[:num_farmers_for_fspawn]
        remaining_farmers_to_farm = remaining_after_wspawn[num_farmers_for_fspawn:]

        # Assign reserved farmer to farm
        environment.assign_group(reserved, "farm")

        # Assign spawn warrior farmers
        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")

        # Assign spawn farmer farmers
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")

        # Assign remaining farmers to farm
        for f in remaining_farmers_to_farm:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Valid cave group_ids: "attack", "cave", "village"
        villagers = list(components)
        for v in villagers:
            role = getattr(v, "role", None)
            if role == "Warrior":
                # All warriors attack when in the cave
                environment.assign_group(v, "attack")
            else:
                # Farmers should return to village
                environment.assign_group(v, "village")