from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # internal step counter to alternate spawn priorities
        self._step_counter = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village assignment:
          - All Warriors -> "cave"
          - Farmers: reserve a small number to farm (to keep wheat flowing).
                     Use remaining farmers in pairs to spawn Warriors (priority on even steps)
                     and spawn Farmers (priority on odd steps), ensuring at least some of both
                     types get produced over time.
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
        # Ensure we always assign all farmers deterministically
        if n_farmers == 0:
            # advance step counter for next call consistency
            self._step_counter += 1
            return

        wheat = getattr(environment.farm, "wheat", 0)

        # Determine reserve: keep 1 farmer farming if wheat is low or few farmers exist,
        # otherwise permit full spawning to grow force.
        if n_farmers <= 2:
            reserve_to_farm = 1
        else:
            # If wheat is small, keep one; if wheat large, allow more spawning (reserve 0)
            reserve_to_farm = 1 if wheat < 20 else 0

        reserve_to_farm = min(reserve_to_farm, n_farmers)
        available = n_farmers - reserve_to_farm

        # Start assignments deterministically from start of farmers list
        idx = 0
        # Assign reserved farmers to farm
        for _ in range(reserve_to_farm):
            environment.assign_group(farmers[idx], group_farm)
            idx += 1

        # If no available farmers for spawns, remaining ones (if any) farm
        if available <= 0:
            while idx < n_farmers:
                environment.assign_group(farmers[idx], group_farm)
                idx += 1
            self._step_counter += 1
            return

        # Alternating priority: even steps prioritize warrior spawns, odd steps prioritize farmer spawns
        prioritize_warrior = (self._step_counter % 2 == 0)

        warrior_spawns = 0
        farmer_spawns = 0

        # Helper to compute how many pairs fit given wheat and available villagers
        def max_pairs_by_wheat(cost_per_spawn, current_wheat):
            return current_wheat // cost_per_spawn

        if prioritize_warrior:
            # Try to spawn as many warriors as possible first
            max_w_by_wheat = max_pairs_by_wheat(12, wheat)
            max_w_pairs_by_villagers = available // 2
            warrior_spawns = min(max_w_by_wheat, max_w_pairs_by_villagers)
            wheat_after_w = wheat - warrior_spawns * 12
            villagers_after_w = available - warrior_spawns * 2

            # If possible, ensure we spawn at least one farmer pair when resources allow
            if villagers_after_w >= 2 and wheat_after_w >= 10:
                farmer_spawns = min(1, villagers_after_w // 2, wheat_after_w // 10)
                wheat_after_w -= farmer_spawns * 10
                villagers_after_w -= farmer_spawns * 2

            # With remaining resources, spawn additional farmer pairs if feasible
            extra_farmer_spawns = min(villagers_after_w // 2, wheat_after_w // 10)
            farmer_spawns += extra_farmer_spawns
        else:
            # Prioritize farmer spawns first to boost wheat production
            max_f_by_wheat = max_pairs_by_wheat(10, wheat)
            max_f_pairs_by_villagers = available // 2
            farmer_spawns = min(max_f_by_wheat, max_f_pairs_by_villagers)
            wheat_after_f = wheat - farmer_spawns * 10
            villagers_after_f = available - farmer_spawns * 2

            # Then spawn warriors with remaining resources
            warrior_spawns = min(wheat_after_f // 12, villagers_after_f // 2)

            # If we still have spare villagers and wheat, allow one more farmer spawn (to ensure both types)
            villagers_left = villagers_after_f - warrior_spawns * 2
            wheat_left = wheat_after_f - warrior_spawns * 12
            if villagers_left >= 2 and wheat_left >= 10:
                farmer_spawns += 1

        # Now perform assignments in deterministic order: warrior pairs, farmer pairs, leftovers farm
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

        # Advance internal counter
        self._step_counter += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave assignment:
          - All Warriors -> "attack"
          - All Farmers -> "village" (send back to village to farm/spawn)
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