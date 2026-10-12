import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Dynamic, tiered spawning strategy with step-aware gating

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors in Village to Cave (immediate attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, Village contains only Farmers (if any)
        available_wheat = environment.farm.wheat
        F = len(farmers)

        # 2) Farmer-spawns: up to 2, bounded by F//2 and wheat//10
        max_f_spawns_base = min(2, F // 2, available_wheat // 10)
        F_spawns = max_f_spawns_base

        wheat_after_f_spawns = available_wheat - (F_spawns * 10)
        remaining_f_after_f_spawns = F - (F_spawns * 2)

        # 3) Warrior-spawns: gated by resources and step/HP
        W_spawns = 0
        turns_left = 30 - step  # how many turns left until 30
        try:
            dragon_hp = environment.dragon.hp
        except Exception:
            dragon_hp = 0

        if turns_left > 15 and dragon_hp > 40:
            if remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24:
                W_spawns = 2
            elif remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                W_spawns = 1
            # Strong early push: if resources allow, push to 2
            if step <= 6 and W_spawns < 2 and remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                W_spawns += 1
        else:
            # Late-game gating (safer)
            if remaining_f_after_f_spawns >= 6 and wheat_after_f_spawns >= 24:
                W_spawns = 2
            elif remaining_f_after_f_spawns >= 4 and wheat_after_f_spawns >= 12:
                W_spawns = 1

        # Safety clamp: ensure we do not allocate more farmers than we have
        total_used = 2 * (F_spawns + W_spawns)
        if total_used > F:
            # Clamp: prioritize Farmer spawns
            max_pairs = F // 2
            F_spawns = min(F_spawns, max_pairs, 2)
            W_spawns = min(W_spawns, max(0, max_pairs - F_spawns))

        idx = 0
        # 4) Assign spawns from Farmers
        for _ in range(F_spawns):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        for _ in range(W_spawns):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 5) Remaining farmers go to farming
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