from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # We'll compute a single final group for each farmer to avoid repeated assignments
        final_farmer = {}

        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Spawn warriors first: each warrior spawn pair requires 2 farmers and 12 wheat
        sp_war_pairs = min(len(farmers) // 2, available_wheat // 12)

        wheat_after_war = max(0, available_wheat - sp_war_pairs * 12)

        # Then spawn farmers with the remaining wheat: each pair requires 2 farmers and 10 wheat
        remaining_farmers_for_war_spawn = len(farmers) - (sp_war_pairs * 2)
        sp_farm_pairs = min(remaining_farmers_for_war_spawn // 2, wheat_after_war // 10)

        idx = 0

        # Assign first sp_war_pairs * 2 farmers to "spawn warrior"
        for _ in range(sp_war_pairs * 2):
            if idx < len(farmers):
                final_farmer[farmers[idx]] = "spawn warrior"
                idx += 1

        # Assign next sp_farm_pairs * 2 farmers to "spawn farmer"
        for _ in range(sp_farm_pairs * 2):
            if idx < len(farmers):
                final_farmer[farmers[idx]] = "spawn farmer"
                idx += 1

        # Remaining farmers stay in the village to farm
        while idx < len(farmers):
            final_farmer[farmers[idx]] = "farm"
            idx += 1

        # Warriors always go to the cave in the village stage
        final_warrior = {w: "cave" for w in warriors}

        # Apply final assignments (one per component)
        for f, grp in final_farmer.items():
            environment.assign_group(f, grp)
        for w, grp in final_warrior.items():
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