from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    """
    Improved adaptation:
    - Village:
        * All Warriors -> "cave"
        * Farmers: be aggressive about spawning warriors as soon as it's affordable.
          - If wheat < 12: all farmers farm.
          - If wheat >= 12 and farmers >= 2:
              - If farmers == 2 and no warriors present locally: use both to spawn a warrior immediately.
              - Otherwise, spawn as many warriors as possible while leaving one farmer to farm (if more than 2 farmers).
              - Then spawn farmers if wheat & pairs remain.
          - Leftover farmers -> "farm"
    - Cave:
        * Farmers -> "village"
        * Warriors with hp <= 1 -> "village" (preserve fragile units)
        * Up to max_attackers highest-HP warriors -> "attack"
        * Remaining warriors in cave -> "cave" (do not attack to limit exposure)
    """
    def assign_in_village(self, components, environment, group_ids, step: int):
        # group_ids: "farm", "cave", "spawn farmer", "spawn warrior"
        villagers = list(components)
        # Partition by role
        warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in villagers if getattr(c, "role", None) == "Farmer"]

        # Send all warriors to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Nothing more to do if no farmers
        if not farmers:
            return

        # Wheat available
        wheat = int(getattr(environment.farm, "wheat", 0))

        num_farmers = len(farmers)
        num_warriors = len(warriors)

        # If can't afford a warrior spawn, farm with everyone
        if wheat < 12:
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # If only exactly 2 farmers and we can afford a warrior spawn,
        # and there are no local warriors (likely none at all), spawn a warrior immediately (use both).
        if num_farmers == 2 and wheat >= 12 and num_warriors == 0:
            # Use both farmers to spawn a warrior
            for f in farmers:
                environment.assign_group(f, "spawn warrior")
            return

        # General case: try to spawn warriors greedily while leaving at least one farmer to farm if possible
        # Reserve one farmer for farming if more than 2 farmers exist; if exactly 2 farmers, allow spawning one warrior (use both)
        reserve_one = num_farmers > 2

        reserve_count = 1 if reserve_one else 0
        available_for_spawn = num_farmers - reserve_count
        pairs_available = available_for_spawn // 2

        # How many warrior spawns by wheat
        max_warrior_spawns_by_wheat = wheat // 12
        warrior_spawns = min(pairs_available, max_warrior_spawns_by_wheat)

        # If we couldn't schedule any warrior spawns but there are exactly 2 farmers and some wheat >=12,
        # allow one spawn (edge-case safety)
        if warrior_spawns == 0 and num_farmers >= 2 and wheat >= 12 and not reserve_one:
            warrior_spawns = 1

        # Assign farmers to spawn warrior
        assigned = set()
        idx = 0
        for _ in range(warrior_spawns):
            # take two farmers for each spawn
            for _ in range(2):
                # skip reserved farm slot(s) at the end
                while idx < len(farmers) and (len(farmers) - idx) <= reserve_count:
                    # these remaining will be reserved for farming
                    idx += 1
                if idx < len(farmers):
                    f = farmers[idx]
                    environment.assign_group(f, "spawn warrior")
                    assigned.add(f)
                    idx += 1

        # Recompute wheat after warrior spawns
        wheat_after_wspawn = wheat - warrior_spawns * 12

        # Now attempt to spawn farmers with remaining pairs (cost 10 wheat each)
        # Count remaining unassigned farmers
        remaining_farmers = [f for f in farmers if f not in assigned]
        # If we reserved one, ensure we keep at least one farming
        # Compute how many remaining can be used for farmer spawns
        reserve_left = reserve_count
        # If there are more than reserve_count remaining, we can use pairs from the rest
        usable_for_fspawn = max(0, len(remaining_farmers) - reserve_left)
        pairs_for_fspawn = usable_for_fspawn // 2
        max_farm_spawns_by_wheat = wheat_after_wspawn // 10
        farmer_spawns = min(pairs_for_fspawn, max_farm_spawns_by_wheat)

        # Assign farmer spawns
        idx2 = 0
        # Skip over reserved farmers at the end: we'll mark those to farm later
        for _ in range(farmer_spawns):
            for _ in range(2):
                # skip reserved area
                while idx2 < len(remaining_farmers) and (len(remaining_farmers) - idx2) <= reserve_left:
                    idx2 += 1
                if idx2 < len(remaining_farmers):
                    f = remaining_farmers[idx2]
                    environment.assign_group(f, "spawn farmer")
                    assigned.add(f)
                    idx2 += 1

        # Finally, any unassigned farmers -> farm
        for f in farmers:
            if f not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # group_ids: "attack", "cave", "village"
        villagers = list(components)
        # Separate farmers and warriors
        farmers = [c for c in villagers if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]

        # Send farmers back to village immediately
        for f in farmers:
            environment.assign_group(f, "village")

        # For warriors: preserve very-low-HP units, allow a small attacking squad
        # Sort warriors by descending hp so high-HP attack first
        warriors_sorted = sorted(warriors, key=lambda x: getattr(x, "hp", 0), reverse=True)

        # Warriors with very low hp should be sent back to village to avoid instant death
        survivors = []
        for w in warriors_sorted:
            hp = getattr(w, "hp", 0)
            if hp <= 1:
                environment.assign_group(w, "village")
            else:
                survivors.append(w)

        # Decide how many attack this turn (small squad to reduce exposure)
        # Use up to 3 attackers (configurable); if total survivors <= 3, let them all attack
        max_attackers = 3
        attackers = survivors[:max_attackers]
        non_attackers = survivors[max_attackers:]

        for a in attackers:
            environment.assign_group(a, "attack")
        for na in non_attackers:
            environment.assign_group(na, "cave")