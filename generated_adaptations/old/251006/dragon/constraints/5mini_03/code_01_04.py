from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village assignment strategy:
          - All Warriors -> "cave"
          - Farmers: reserve 1 farmer to "farm" (if any exist) to keep wheat flowing.
                     From remaining farmers, in pairs:
                       * spawn as many Warriors ("spawn warrior") as wheat and pairs allow (priority)
                       * then spawn Farmers ("spawn farmer") if wheat/pairs remain
                     Leftover farmers -> "farm"
        Ensures every component is assigned exactly once.
        """
        # Helper to get a valid group id (fallback to first valid if missing)
        def g(name):
            return name if name in group_ids else group_ids[0]

        group_cave = g("cave")
        group_farm = g("farm")
        group_spawn_w = g("spawn warrior")
        group_spawn_f = g("spawn farmer")

        # Partition components by role, preserving a deterministic order
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # Assign all warriors to cave
        for w in warriors:
            environment.assign_group(w, group_cave)

        n_farmers = len(farmers)
        if n_farmers == 0:
            return  # nothing more to assign in village

        # Current wheat
        wheat = getattr(environment.farm, "wheat", 0)

        # Reserve a single farmer to farm if possible to keep wheat flowing
        reserve_to_farm = 1 if n_farmers >= 1 else 0

        # Determine how many farmers are available for spawning/farming beyond reserve
        available_for_spawns = n_farmers - reserve_to_farm
        if available_for_spawns < 0:
            available_for_spawns = 0

        # Determine maximum warrior spawns by wheat and available pairs
        max_warrior_by_wheat = wheat // 12
        max_warrior_pairs_by_villagers = available_for_spawns // 2
        warrior_spawns = min(max_warrior_by_wheat, max_warrior_pairs_by_villagers)

        # Account for wheat used by warrior spawns
        wheat_after_w = wheat - warrior_spawns * 12

        # Remaining villagers after warrior spawn allocation
        villagers_left_after_w = available_for_spawns - warrior_spawns * 2

        # Determine farmer spawns
        max_farmer_by_wheat = wheat_after_w // 10
        farmer_spawns = min(max_farmer_by_wheat, villagers_left_after_w // 2)

        # Now perform deterministic assignments:
        # - First reserve farmer(s) to farm
        # - Then assign pairs for warrior spawns
        # - Then assign pairs for farmer spawns
        # - Remaining farmers farm

        idx = 0
        # Reserve farmers to farm
        for _ in range(reserve_to_farm):
            environment.assign_group(farmers[idx], group_farm)
            idx += 1

        # Assign warrior spawn pairs
        for _ in range(warrior_spawns):
            # take two farmers
            environment.assign_group(farmers[idx], group_spawn_w); idx += 1
            environment.assign_group(farmers[idx], group_spawn_w); idx += 1

        # Assign farmer spawn pairs
        for _ in range(farmer_spawns):
            environment.assign_group(farmers[idx], group_spawn_f); idx += 1
            environment.assign_group(farmers[idx], group_spawn_f); idx += 1

        # Any leftover farmers farm
        while idx < n_farmers:
            environment.assign_group(farmers[idx], group_farm)
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave assignment strategy:
          - All Warriors -> "attack"
          - All Farmers -> "village" (send back to village to farm / spawn)
        Ensures every component is assigned exactly once.
        """
        def g(name):
            return name if name in group_ids else group_ids[0]

        group_attack = g("attack")
        group_village = g("village")

        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                environment.assign_group(c, group_attack)
            else:
                environment.assign_group(c, group_village)