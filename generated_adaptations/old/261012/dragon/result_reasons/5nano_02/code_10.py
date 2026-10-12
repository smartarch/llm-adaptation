import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Tiered, risk-aware spawning strategy:
        # - Move all Warriors in Village to Cave
        # - Spawn Farmer and Warrior spawns with a dynamic cap dependent on step and Dragon HP
        # - Remaining Farmers stay in Village and farm

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all existing Warriors in Village to Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, in Village there are only Farmers (if any)
        available_wheat = environment.farm.wheat
        F = len(farmers)

        # 2) Tiered spawning policy
        # Base spawns (conservative cap of 2 per type)
        max_f_spawns_base = min(2, F // 2, available_wheat // 10)

        # Wheat left after farmer spawns
        wheat_after_f_spawns = available_wheat - (max_f_spawns_base * 10)
        remaining_f_after_f_spawns = F - (max_f_spawns_base * 2)

        max_w_spawns_base = min(2, remaining_f_after_f_spawns // 2, wheat_after_f_spawns // 12)

        F_spawns = max_f_spawns_base
        W_spawns = max_w_spawns_base

        # Tiered aggressiveness
        # If Dragon HP is high and we have resources, allow one extra spawn per type
        extra = 0
        try:
            # Some environments may not have dragon hp accessible; guard gracefully
            if getattr(environment, "dragon", None) is not None:
                dragon_hp = environment.dragon.hp
                # Aggressive mode when dragon hp is high and steps are still early
                if dragon_hp > 30 and step <= 12:
                    extra = 1
                elif dragon_hp > 40 and step <= 16:
                    extra = 1
        except Exception:
            extra = 0

        F_spawns = min(2, F_spawns + extra)
        # Recompute Warrior spawns with potential extra
        # Recalculate with updated F_spawns to ensure we don't exceed available farmers
        remaining_f = F - (F_spawns * 2)
        wheat_after = wheat_after_f_spawns
        W_spawns = min(2, remaining_f // 2, wheat_after // 12)

        # Safety clamp: ensure we do not allocate more villagers than we have
        total_used = 2 * (F_spawns + W_spawns)
        if total_used > F:
            # Clamp proportionally, prioritizing Farmer spawns
            max_pairs = F // 2
            F_spawns = min(F_spawns, max_pairs)
            W_spawns = min(W_spawns, max(0, max_pairs - F_spawns))

        # 3) Assign spawns from Farmers
        idx = 0
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
        # - All Warriors in Cave should attack Dragon
        # - All Farmers in Cave should go back to Village

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")