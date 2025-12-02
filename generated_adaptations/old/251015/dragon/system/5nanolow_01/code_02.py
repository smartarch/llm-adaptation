from.generated_adaptations.base_classes.dragon import DragonHuntAdaptation  # import path as described

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - All Warriors should be assigned to "cave" in general (not here).
        # - In village: handle Farmers
        #   * Partition Farmers into: spawn_farm, spawn_warrior, farm
        # - Use farm.wheat as resource to decide spawning counts
        # - Use as many pairs as possible given wheat:
        #     pf = min(F // 2, W // 10)  -> number of pairs for spawn farmer
        #     remaining wheat = W - pf*10
        #     pw = min((F - 2*pf) // 2, remaining_W // 12) -> pairs for spawn warrior
        #     k_farm_spawn = 2 * pf
        #     k_warrior_spawn = 2 * pw
        # - All remaining farmers go to "farm".
        # - If there are any Warriors among components (unexpected in village), send them to "cave" (attack) group
        #
        # Note: components is a list of villager objects with attributes 'role' and 'hp'
        # We only use their role to categorize.
        group_for_assign = {group: [] for group in group_ids}

        # Collect farmers and warriors (safety for unexpected roles)
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # If any warriors present in village (unusual per rules but handle gracefully)
        for w in warriors:
            group_for_assign["cave"].append(w)

        # If any farmers present in cave, keep them in cave (or move to village? We'll keep in cave)
        # But we only have villagers in village here; this is a best-effort.

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        F = len(farmers)
        # Number of pairs for spawning farmers
        pf = min(F // 2, wheat // 10)
        k_farm_spawn = 2 * pf
        wheat -= pf * 10

        # Remaining farmers after taking those for spawn farmer
        remaining_after_pf = F - k_farm_spawn
        # Pairs for spawning warriors
        pw = min(remaining_after_pf // 2, wheat // 12)
        k_war_spawn = 2 * pw
        wheat -= pw * 12

        # Now allocate villagers to groups
        # First, assign k_farm_spawn farmers to "spawn farmer"
        if k_farm_spawn > 0:
            for f in farmers[:k_farm_spawn]:
                group_for_assign["spawn farmer"].append(f)
        # Then assign next k_war_spawn farmers to "spawn warrior"
        if k_war_spawn > 0:
            for f in farmers[k_farm_spawn:k_farm_spawn + k_war_spawn]:
                group_for_assign["spawn warrior"].append(f)
        # Remaining farmers go to "farm"
        remaining_farmers = farmers[k_farm_spawn + k_war_spawn:]
        for f in remaining_farmers:
            group_for_assign["farm"].append(f)

        # Finally, ensure everyone is assigned to something
        # (In case there were any villagers not Farmers or Warriors)
        unassigned = [c for c in components if c not in sum(group_for_assign.values(), [])]
        for c in unassigned:
            # Default to farming
            group_for_assign["farm"].append(c)

        # Now perform the assignments
        for gid, lst in group_for_assign.items():
            for c in lst:
                environment.assign_group(c, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy:
        # - All Warriors should be in the "attack" group to attack the Dragon.
        # - All Farmers should stay in the cave or move to village if needed.
        group_for_assign = {group: [] for group in group_ids}

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                group_for_assign["attack"].append(c)
            elif role == "Farmer":
                # Farmers staying in cave (as per rule "All Farmers should stay in Village").
                # To comply with "stay in Cave" requirement in this function, we place them in cave.
                group_for_assign["cave"].append(c)
            else:
                # Unknown role: keep in cave as safe default
                group_for_assign["cave"].append(c)

        for gid, lst in group_for_assign.items():
            for c in lst:
                environment.assign_group(c, gid)