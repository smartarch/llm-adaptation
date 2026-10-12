from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors among villagers in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Determine final assignment for each farmer in a single pass
        final_group_for_farmer = {}

        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Determine how many farmer-spawn pairs we can do this step
        max_farm_pairs_by_wheat = available_wheat // 10 if available_wheat >= 10 else 0
        max_farm_pairs_by_count = len(farmers) // 2
        sp_farm_pairs = min(2, max_farm_pairs_by_wheat, max_farm_pairs_by_count)

        # Wheat remaining after farmer spawns
        wheat_after_farm_spawns = max(0, available_wheat - sp_farm_pairs * 10)

        # Remaining farmers available for warrior-spawns
        used_for_farm_spawns = sp_farm_pairs * 2
        remaining_farmers_for_war_spawn = len(farmers) - used_for_farm_spawns

        # Determine how many warrior-spawn pairs we can do this step
        max_war_pairs_by_wheat = wheat_after_farm_spawns // 12 if wheat_after_farm_spawns >= 12 else 0
        sp_war_pairs = min(2, max_war_pairs_by_wheat, remaining_farmers_for_war_spawn // 2)

        # Assign farmers to their final groups in a single pass
        idx = 0
        # First 2*sp_farm_pairs farmers -> "spawn farmer"
        for _ in range(sp_farm_pairs * 2):
            if idx < len(farmers):
                final_group_for_farmer[farmers[idx]] = "spawn farmer"
                idx += 1

        # Next 2*sp_war_pairs farmers -> "spawn warrior"
        for _ in range(sp_war_pairs * 2):
            if idx < len(farmers):
                final_group_for_farmer[farmers[idx]] = "spawn warrior"
                idx += 1

        # Remaining farmers -> "farm"
        while idx < len(farmers):
            final_group_for_farmer[farmers[idx]] = "farm"
            idx += 1

        # Warriors: always move to the cave in village stage
        final_group_for_warrior = {w: "cave" for w in warriors}

        # Apply final assignments (exactly one assignment per component)
        for f, grp in final_group_for_farmer.items():
            environment.assign_group(f, grp)
        for w, grp in final_group_for_warrior.items():
            environment.assign_group(w, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack, Farmers return to the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors attack
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers go back to the Village
        for f in farmers:
            environment.assign_group(f, "village")