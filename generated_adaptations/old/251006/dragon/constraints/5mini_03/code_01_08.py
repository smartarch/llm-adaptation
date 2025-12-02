from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._step_counter = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village assignment:
          - All Warriors -> "cave"
          - Farmers: aggressively spawn when possible.
            * Reserve 0 farmers except when exactly 1 farmer exists (reserve 1).
            * If resources allow (>=2 pairs and >=22 wheat), ensure at least one warrior and one farmer spawn.
            * Then prioritize spawning warriors, then farmers with remaining pairs/wheat.
          - Assign any leftover farmers to "farm".
        """
        def g(name):
            return name if name in group_ids else group_ids[0]

        group_cave = g("cave")
        group_farm = g("farm")
        group_spawn_w = g("spawn warrior")
        group_spawn_f = g("spawn farmer")

        # Partition villagers by role
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # Send all warriors to cave
        for w in warriors:
            environment.assign_group(w, group_cave)

        n_farmers = len(farmers)
        # If no farmers, nothing more to assign
        if n_farmers == 0:
            self._step_counter += 1
            return

        wheat = getattr(environment.farm, "wheat", 0)

        # Reserve logic: keep 1 farmer only if exactly 1 farmer exists (so they don't vanish)
        reserve_to_farm = 1 if n_farmers == 1 else 0

        # Available villagers for spawning/farming beyond reserve
        available_for_spawns = n_farmers - reserve_to_farm
        if available_for_spawns < 0:
            available_for_spawns = 0

        available_pairs = available_for_spawns // 2

        warrior_spawns = 0
        farmer_spawns = 0
        wheat_left = wheat
        pairs_left = available_pairs

        # If we can and have at least two pairs and >= 22 wheat, ensure both a warrior and a farmer are spawned
        if pairs_left >= 2 and wheat_left >= 22:
            # allocate one warrior spawn (12) and one farmer spawn (10)
            warrior_spawns += 1
            farmer_spawns += 1
            wheat_left -= 12 + 10
            pairs_left -= 2

        # With remaining resources, prioritize warrior spawns
        if pairs_left > 0 and wheat_left >= 12:
            max_w_by_wheat = wheat_left // 12
            w_add = min(pairs_left, max_w_by_wheat)
            warrior_spawns += w_add
            pairs_left -= w_add
            wheat_left -= w_add * 12

        # With remaining resources, spawn farmers
        if pairs_left > 0 and wheat_left >= 10:
            max_f_by_wheat = wheat_left // 10
            f_add = min(pairs_left, max_f_by_wheat)
            farmer_spawns += f_add
            pairs_left -= f_add
            wheat_left -= f_add * 10

        # Now perform assignments deterministically:
        idx = 0
        # Reserve farmer(s) to farm if any reserved
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