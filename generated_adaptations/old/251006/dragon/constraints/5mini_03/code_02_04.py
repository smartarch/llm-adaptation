from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._step_counter = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village assignment:
          - All Warriors -> "cave"
          - Farmers: reserve 1 only if exactly 1 farmer exists, otherwise reserve 0.
                     Use remaining farmers in pairs to spawn (ensure at least one of each kind
                     if resources allow), prioritize warrior spawns, then farmer spawns.
                     Leftovers farm.
        """
        def g(name):
            return name if name in group_ids else group_ids[0]

        group_cave = g("cave")
        group_farm = g("farm")
        group_spawn_w = g("spawn warrior")
        group_spawn_f = g("spawn farmer")

        # Deterministic partition
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # Assign all warriors to cave (requirement)
        for w in warriors:
            environment.assign_group(w, group_cave)

        n_farmers = len(farmers)
        if n_farmers == 0:
            self._step_counter += 1
            return

        wheat = getattr(environment.farm, "wheat", 0)

        # Reserve policy: keep 1 farmer only if there's exactly 1 farmer
        reserve_to_farm = 1 if n_farmers == 1 else 0

        available_for_spawns = n_farmers - reserve_to_farm
        available_pairs = max(0, available_for_spawns // 2)

        warrior_spawns = 0
        farmer_spawns = 0
        wheat_left = wheat
        pairs_left = available_pairs

        # If we can, ensure at least one warrior and one farmer spawn when resources are adequate
        if pairs_left >= 2 and wheat_left >= 22:
            warrior_spawns += 1
            farmer_spawns += 1
            wheat_left -= 12 + 10
            pairs_left -= 2

        # Prioritize warrior spawns with remaining resources
        if pairs_left > 0 and wheat_left >= 12:
            max_w_by_wheat = wheat_left // 12
            w_add = min(pairs_left, max_w_by_wheat)
            warrior_spawns += w_add
            pairs_left -= w_add
            wheat_left -= w_add * 12

        # Then spawn farmers with any remaining resources
        if pairs_left > 0 and wheat_left >= 10:
            max_f_by_wheat = wheat_left // 10
            f_add = min(pairs_left, max_f_by_wheat)
            farmer_spawns += f_add
            pairs_left -= f_add
            wheat_left -= f_add * 10

        # Now perform deterministic assignments:
        idx = 0
        # Reserve farmer(s) to farm
        for _ in range(reserve_to_farm):
            environment.assign_group(farmers[idx], group_farm)
            idx += 1

        # Assign warrior spawn pairs
        for _ in range(warrior_spawns):
            if idx + 1 < n_farmers:
                environment.assign_group(farmers[idx], group_spawn_w); idx += 1
                environment.assign_group(farmers[idx], group_spawn_w); idx += 1
            else:
                break

        # Assign farmer spawn pairs
        for _ in range(farmer_spawns):
            if idx + 1 < n_farmers:
                environment.assign_group(farmers[idx], group_spawn_f); idx += 1
                environment.assign_group(farmers[idx], group_spawn_f); idx += 1
            else:
                break

        # Any leftover farmers farm
        while idx < n_farmers:
            environment.assign_group(farmers[idx], group_farm)
            idx += 1

        self._step_counter += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave assignment:
          - All Warriors -> "attack"
          - All Farmers -> "village"
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