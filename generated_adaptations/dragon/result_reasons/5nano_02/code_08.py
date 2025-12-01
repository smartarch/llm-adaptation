import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors in Village to Cave (to ensure immediate attack capability)
        # - Spawn up to 2 Farmer-spawns (if resources allow) to increase wheat production
        # - With remaining Farmers, spawn up to 2 Warrior-spawns to increase DPS
        # - Remaining Farmers go to farming to sustain wheat production

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all existing Warriors in Village to Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, Village contains only Farmers (if any)
        available_wheat = environment.farm.wheat
        F = len(farmers)

        # 2) Compute bounded spawns
        # Farmer-spawns: each uses 2 farmers and 10 wheat, cap at 2 spawns
        max_f_spawns = min(2, F // 2, available_wheat // 10)
        F_spawns = max_f_spawns

        wheat_after_f_spawns = available_wheat - (F_spawns * 10)
        remaining_farmers_after_f_spawns = F - (F_spawns * 2)

        # Warrior-spawns: each uses 2 farmers and 12 wheat, cap at 2 spawns
        max_w_spawns = min(2, remaining_farmers_after_f_spawns // 2, wheat_after_f_spawns // 12)
        W_spawns = max_w_spawns

        # Safety: ensure we do not over-allocate farmers beyond what's available
        total_used_villagers = 2 * (F_spawns + W_spawns)
        if total_used_villagers > F:
            # clamp spawns conservatively
            F_spawns = min(F // 2, 2)
            W_spawns = min(2, (F - 2 * F_spawns) // 2)

        idx = 0
        # 3) Assign spawns from Farmers
        for _ in range(F_spawns):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        for _ in range(W_spawns):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 4) Remaining farmers go to farming
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy in Cave:
        # - All Warriors in Cave should attack Dragon ("attack")
        # - All Farmers in Cave should go back to Village ("village")
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")