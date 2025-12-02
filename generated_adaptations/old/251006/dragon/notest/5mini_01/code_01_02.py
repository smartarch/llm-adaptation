from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Village
        group_ids: valid groups = ["farm", "cave", "spawn farmer", "spawn warrior"]
        """
        # Ensure group names are exactly those expected
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # 1) Send all warriors to cave
        for w in warriors:
            environment.assign_group(w, CAVE)

        # 2) Decide how many farmers to assign to spawning vs farming
        total_farmers = len(farmers)
        # Keep at least this many farmers farming to maintain wheat production
        min_farmers_farming = 2
        if total_farmers <= min_farmers_farming:
            # Not enough farmers to spare: all farm
            for f in farmers:
                environment.assign_group(f, FARM)
            return

        # Available wheat
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Number of spare farmers available for spawning (beyond the reserved ones)
        spare_farmers = total_farmers - min_farmers_farming
        spare_pairs = spare_farmers // 2  # each spawn requires 2 villagers

        # How many warrior spawns possible by wheat and by spare pairs
        max_warriors_by_wheat = wheat // 12
        warrior_spawn_count = min(spare_pairs, max_warriors_by_wheat)

        # Reserve farmers for warrior spawns
        farmers_for_warrior = warrior_spawn_count * 2
        wheat_after_warrior = wheat - warrior_spawn_count * 12
        spare_farmers_after_warrior = spare_farmers - farmers_for_warrior
        spare_pairs_after_warrior = spare_farmers_after_warrior // 2

        # Now compute farmer spawns
        max_farmers_by_wheat = wheat_after_warrior // 10
        farmer_spawn_count = min(spare_pairs_after_warrior, max_farmers_by_wheat)
        farmers_for_farmer = farmer_spawn_count * 2

        # Assign specific farmer components:
        # We'll take farmers in list order:
        idx = 0
        # assign those designated for warrior spawn
        for _ in range(farmers_for_warrior):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], SPAWN_WARRIOR)
                idx += 1
        # assign those designated for farmer spawn
        for _ in range(farmers_for_farmer):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], SPAWN_FARMER)
                idx += 1
        # remaining farmers farm
        while idx < total_farmers:
            environment.assign_group(farmers[idx], FARM)
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Cave
        group_ids: valid groups = ["attack", "cave", "village"]
        """
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                # All warriors should attack
                environment.assign_group(c, ATTACK)
            else:
                # Farmers should not remain in the Cave; send them back to Village
                environment.assign_group(c, VILLAGE)