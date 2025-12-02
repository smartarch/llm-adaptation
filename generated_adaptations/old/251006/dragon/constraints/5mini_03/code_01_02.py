from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Village
        group_ids: list of valid group names
        Strategy:
          - Send all Warriors to the "cave".
          - Keep a small reserve of farmers farming to produce wheat.
          - Use remaining farmers in pairs to spawn Warriors (priority) as allowed by wheat.
          - If wheat remains and extra farmer pairs exist, spawn Farmers.
          - Assign leftover farmers to "farm".
        """
        # Helper to check group availability, fall back to first valid if missing (robustness)
        def valid_group(name):
            return name if name in group_ids else group_ids[0]

        group_cave = valid_group("cave")
        group_farm = valid_group("farm")
        group_spawn_w = valid_group("spawn warrior")
        group_spawn_f = valid_group("spawn farmer")

        # Separate villagers by role
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # 1) Send all warriors to cave
        for w in warriors:
            environment.assign_group(w, group_cave)

        # 2) Decide farmer assignments
        n_farmers = len(farmers)
        if n_farmers == 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)
        # Reserve some farmers to always farm to sustain wheat production.
        reserve_to_farm = 2 if n_farmers >= 2 else 1
        reserve_to_farm = min(reserve_to_farm, n_farmers)

        # Assign reserved farmers to farm
        farmers_sorted = list(farmers)  # copy for deterministic selection
        reserved = farmers_sorted[:reserve_to_farm]
        for f in reserved:
            environment.assign_group(f, group_farm)

        remaining = farmers_sorted[reserve_to_farm:]
        remaining_count = len(remaining)

        # Estimate how many warrior spawns we can afford (each spawn warrior consumes 12 wheat and requires 2 villagers)
        max_warriors_by_wheat = wheat // 12
        max_warrior_pairs_by_villagers = remaining_count // 2
        warrior_pairs = min(max_warriors_by_wheat, max_warrior_pairs_by_villagers)

        # Assign pairs to spawn warrior
        idx = 0
        for _ in range(warrior_pairs):
            # take two farmers
            for _ in range(2):
                environment.assign_group(remaining[idx], group_spawn_w)
                idx += 1
            wheat -= 12  # account for estimated consumption

        # With wheat remaining, consider spawning farmers (10 wheat per spawn, 2 villagers per spawn)
        remaining_after_w = remaining[idx:]
        remaining_after_count = len(remaining_after_w)
        max_farmers_by_wheat = wheat // 10
        farmer_pairs = min(remaining_after_count // 2, max_farmers_by_wheat)

        idx2 = 0
        for _ in range(farmer_pairs):
            for _ in range(2):
                environment.assign_group(remaining_after_w[idx2], group_spawn_f)
                idx2 += 1
            wheat -= 10

        # Any leftover farmers farm
        leftover = remaining_after_w[idx2:]
        for f in leftover:
            environment.assign_group(f, group_farm)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Cave
        group_ids: list of valid group names
        Strategy:
          - All Warriors -> "attack"
          - All Farmers -> return to "village" so they can farm/spawn
        """
        def valid_group(name):
            return name if name in group_ids else group_ids[0]

        group_attack = valid_group("attack")
        group_village = valid_group("village")
        # group 'cave' exists but per strategy we keep warriors attacking and farmers returning.

        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                environment.assign_group(c, group_attack)
            else:
                # farmers and any non-warriors go back to village
                environment.assign_group(c, group_village)