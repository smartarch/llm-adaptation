from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = environment.farm.wheat

        # Compute maximum possible spawns given current wheat and farmers
        spawn_farm_spawns = min(F // 2, W // 10)  # number of Farmer-spawns (each uses 2 farmers and 10 wheat)
        W_after_farm_spawns = W - 10 * spawn_farm_spawns
        F_after_farm_spawns = F - 2 * spawn_farm_spawns

        spawn_warrior_spawns = min(F_after_farm_spawns // 2, W_after_farm_spawns // 12)  # each uses 2 farmers and 12 wheat
        W_after_all_spawns = W_after_farm_spawns - 12 * spawn_warrior_spawns
        F_after_all_spawns = F_after_farm_spawns - 2 * spawn_warrior_spawns

        # Final group sizes for Farmers
        farm_group_size = F_after_all_spawns
        spawn_farmer_group_size = 2 * spawn_farm_spawns
        spawn_warrior_group_size = 2 * spawn_warrior_spawns

        # Assign Farmers to "farm", "spawn farmer", or "spawn warrior"
        # The order is deterministic: first farm, then spawn farmer, then spawn warrior
        idx = 0
        for c in farmers:
            if idx < farm_group_size:
                environment.assign_group(c, "farm")
            elif idx < farm_group_size + spawn_farmer_group_size:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "spawn warrior")
            idx += 1

        # All Warriors go to cave (to move to cave and later attack)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors should attack, Farmers should go back to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")