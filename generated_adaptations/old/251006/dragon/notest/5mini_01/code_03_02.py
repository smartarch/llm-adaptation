from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village groups: "farm", "cave", "spawn farmer", "spawn warrior"
        Strategy:
        - All Warriors -> "cave"
        - Keep at least 2 Farmers farming to sustain wheat.
        - Use spare Farmers in pairs to spawn warriors whenever wheat >= 12.
          Prioritize warrior spawns. Allow multiple warrior spawns if wheat and spare pairs permit,
          but keep at least 2 farmers farming.
        - After warrior spawns, if spare pairs and wheat remain, spawn farmers.
        """
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Split components by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # 1) Send all warriors to the Cave (as requested)
        for w in warriors:
            environment.assign_group(w, CAVE)

        # 2) Farmers handling: keep reserve for farming
        total_farmers = len(farmers)
        # Reserve at least 2 farmers to farm (or as many as available if less than 2)
        reserve_farmers = 2 if total_farmers >= 2 else total_farmers
        spare_farmers = max(0, total_farmers - reserve_farmers)
        spare_pairs = spare_farmers // 2

        # Wheat available
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Determine warrior spawns:
        # We allow as many warrior spawns as pairs and wheat allow, but cap to avoid draining all farmers:
        # Cap new warrior spawns per step to at most 3 to avoid exhausting population in one go.
        max_warriors_by_wheat = wheat // 12
        warrior_spawns = min(spare_pairs, max_warriors_by_wheat, 3)

        # If we have very few farmers overall, avoid spawning so we preserve farmers (guard)
        if total_farmers < 4:
            # require at least 4 farmers to start spawning warriors (so reserve 2 remain)
            warrior_spawns = 0

        farmers_used_for_warriors = warrior_spawns * 2
        wheat_after_warriors = wheat - warrior_spawns * 12
        spare_farmers_after_warriors = spare_farmers - farmers_used_for_warriors
        spare_pairs_after_warriors = spare_farmers_after_warriors // 2

        # Determine farmer spawns with remaining wheat (10 wheat per farmer spawn)
        max_farmers_by_wheat = wheat_after_warriors // 10
        farmer_spawns = min(spare_pairs_after_warriors, max_farmers_by_wheat)

        # Do not spawn farmers if that would reduce reserve below 2
        # (spare_farmers_after_warriors already accounts for reserve of 2)
        farmers_used_for_farmers = farmer_spawns * 2

        # Now assign farmer components: choose in list order
        idx = 0
        # Assign those for warrior spawn
        for _ in range(farmers_used_for_warriors):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], SPAWN_WARRIOR)
                idx += 1
        # Assign those for farmer spawn
        for _ in range(farmers_used_for_farmers):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], SPAWN_FARMER)
                idx += 1
        # Remaining farmers farm
        while idx < total_farmers:
            environment.assign_group(farmers[idx], FARM)
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave groups: "attack", "cave", "village"
        Strategy:
        - All Warriors in Cave -> "attack"
        - Any Farmers in Cave -> immediately send to "village"
        """
        ATTACK = "attack"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, ATTACK)
            else:
                # Farmers must be returned to Village to keep fields safe and produce wheat
                environment.assign_group(c, VILLAGE)