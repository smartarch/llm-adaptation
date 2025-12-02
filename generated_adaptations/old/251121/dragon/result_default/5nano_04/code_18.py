from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave (for Warriors)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned

        Strategy (bounded aggressive spawning with wheat reserve):
        - Move all Warriors to the cave (they will attack Dragon).
        - Compute a wheat reserve that scales with Dragon HP to avoid starving farming.
        - Spawn Farmers first up to the cap (needs 10 wheat per 2 Farmers).
        - Then spawn Warriors from the remaining Farmers (needs 12 wheat per 2 Farmers).
        - The rest of Farmers stay in Farm.
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        total_farmers = len(farmers)

        # Move all warriors to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        if total_farmers == 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)
        dragon_hp = getattr(environment.dragon, "hp", 0)

        # Wheat reserve heuristic (scales with Dragon HP)
        # More HP => smaller reserve; as HP drops, keep a slightly larger reserve
        if dragon_hp > 60:
            reserve = 0
        elif dragon_hp > 40:
            reserve = 2
        elif dragon_hp > 20:
            reserve = 4
        else:
            reserve = 6

        max_spend = max(0, wheat - reserve)

        # Spawn Farmers first
        spawn_farm_pairs = 0
        if total_farmers >= 2 and max_spend >= 10:
            spawn_farm_pairs = min(total_farmers // 2, max_spend // 10)
        spawn_farm_count = 2 * spawn_farm_pairs

        remaining_farmers_after_farm = total_farmers - spawn_farm_count
        wheat_after_farm = wheat - (spawn_farm_pairs * 10)

        # Then spawn Warriors from remaining farmers
        spawn_war_pairs = 0
        if remaining_farmers_after_farm >= 2 and wheat_after_farm >= 12:
            spawn_war_pairs = min(remaining_farmers_after_farm // 2, wheat_after_farm // 12)
        spawn_war_count = 2 * spawn_war_pairs

        farm_count = remaining_farmers_after_farm - spawn_war_count

        idx = 0
        # Assign to spawn farmer
        for _ in range(spawn_farm_count):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        # Assign to spawn warrior
        for _ in range(spawn_war_count):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        # Assign remaining to farm
        for _ in range(farm_count):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Edge-case safety: any leftover farmers go to farm
        while idx < total_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village

        Strategy:
        - All Warriors attack; Farmers go to Village to continue farming/spawning.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")