from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    """
    Adaptation that protects the farming backbone while still spawning warriors:
    - Village:
      * All Warriors -> "cave"
      * Reserve up to 2 Farmers to "farm" (if available) to keep wheat income stable.
      * Use surplus Farmers (beyond reserved) in pairs to spawn Warriors when wheat allows.
      * Only spawn Farmers rarely (when wheat is large) to avoid draining the backbone.
      * Special-case: if exactly 2 Farmers and no Warriors exist, and wheat >= 12, use both to spawn one Warrior
        (to bootstrap combat capability).
    - Cave:
      * Farmers -> "village"
      * Warriors with hp <= 1 -> "village" (rotate out fragile units)
      * Up to max_attackers healthiest Warriors -> "attack"
      * Remaining Warriors -> "cave"
    """
    def assign_in_village(self, components, environment, group_ids, step: int):
        # Valid village group_ids: "farm", "cave", "spawn farmer", "spawn warrior"
        villagers = list(components)
        warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in villagers if getattr(c, "role", None) == "Farmer"]

        # Send all warriors to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        wheat = int(getattr(environment.farm, "wheat", 0))
        num_farmers = len(farmers)
        num_warriors = len(warriors)

        # Bootstrap rule: if exactly 2 farmers and no warriors exist, spawn one warrior immediately if affordable
        if num_farmers == 2 and num_warriors == 0 and wheat >= 12:
            # Use both farmers to spawn a warrior
            for f in farmers:
                environment.assign_group(f, "spawn warrior")
            return

        # Reserve up to 2 farmers to farm (to protect the fields)
        reserve_farmers = min(2, num_farmers)
        # The farmers that are available for spawning are those beyond the reserve
        available_for_spawn = num_farmers - reserve_farmers

        # Compute how many warrior spawns can be done (2 farmers and 12 wheat each)
        warrior_pairs_available = available_for_spawn // 2
        warrior_spawns_by_wheat = wheat // 12
        warrior_spawns = min(warrior_pairs_available, warrior_spawns_by_wheat)

        assigned = set()

        # Assign spawn warrior groups from the surplus farmers (choose deterministic farmers to spawn)
        # We'll pick from the end of the farmers list so the first reserved farmers remain farming.
        spawn_candidates = farmers[reserve_farmers:]  # these are surplus
        idx = 0
        for _ in range(warrior_spawns):
            # take two candidates per warrior spawn
            for _ in range(2):
                if idx < len(spawn_candidates):
                    f = spawn_candidates[idx]
                    environment.assign_group(f, "spawn warrior")
                    assigned.add(f)
                    idx += 1

        wheat_after_wspawn = wheat - warrior_spawns * 12

        # Optionally spawn farmers only if large wheat surplus and many surplus farmers remain
        # This keeps the backbone intact by default.
        spawn_farmer_spawns = 0
        # Conditions to allow farmer spawns: at least 2 spare pairs remain and wheat >= 40 (tunable)
        remaining_spare = len(spawn_candidates) - idx
        spare_pairs = remaining_spare // 2
        if spare_pairs >= 2 and wheat_after_wspawn >= 40:
            # spawn as many farmer spawns as sensible (but don't exceed spare_pairs or wheat)
            spawn_farmer_spawns = min(spare_pairs, wheat_after_wspawn // 10)

        # Assign spawn farmer groups
        for _ in range(spawn_farmer_spawns):
            for _ in range(2):
                if idx < len(spawn_candidates):
                    f = spawn_candidates[idx]
                    environment.assign_group(f, "spawn farmer")
                    assigned.add(f)
                    idx += 1

        # Finally, ensure that reserve farmers farm
        for i in range(reserve_farmers):
            f = farmers[i]
            if f not in assigned:
                environment.assign_group(f, "farm")

        # Any remaining unassigned surplus farmers (that were not used for spawns) should also farm
        for j in range(reserve_farmers, len(farmers)):
            f = farmers[j]
            if f not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Valid cave group_ids: "attack", "cave", "village"
        villagers = list(components)
        farmers = [c for c in villagers if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]

        # Send farmers back to village immediately
        for f in farmers:
            environment.assign_group(f, "village")

        # Protect very-low HP warriors by rotating them back
        warriors_sorted = sorted(warriors, key=lambda x: getattr(x, "hp", 0), reverse=True)

        survivors = []
        for w in warriors_sorted:
            hp = getattr(w, "hp", 0)
            if hp <= 1:
                environment.assign_group(w, "village")
            else:
                survivors.append(w)

        # Choose a modest attacking squad to reduce exposure
        max_attackers = 3
        attackers = survivors[:max_attackers]
        non_attackers = survivors[max_attackers:]

        for a in attackers:
            environment.assign_group(a, "attack")
        for na in non_attackers:
            environment.assign_group(na, "cave")