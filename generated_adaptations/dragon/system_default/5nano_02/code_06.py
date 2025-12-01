from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Default: Warriors -> cave (attack), Farmers -> farm (village)
        # - Early DPS boost: move up to 2 Farmers to cave to increase initial damage
        # - Spawning pipeline:
        #   1) Spawn Farmers using pairs of villagers in village and available wheat (10 wheat per new Farmer)
        #   2) With remaining wheat, spawn Warriors using pairs of villagers in village
        # - Any remaining unassigned villagers stay in farm

        mapping = {}

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default assignments
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                mapping[c] = "cave"  # go to Cave
            else:
                mapping[c] = "farm"  # stay in Village and farm

        # Step 1: Early DPS push - move up to 2 Farmers to Cave for extra damage
        available_farmers_for_attack = [f for f in farmers if mapping.get(f) != "cave"]
        two_to_move = min(2, len(available_farmers_for_attack))
        for i in range(two_to_move):
            mapping[available_farmers_for_attack[i]] = "cave"

        # Step 2: Spawning planning based on wheat in the Farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = getattr(environment.farm, "wheat", 0)

        # 2a. Spawn Farmers: take from villagers not currently in cave, in pairs
        candidates_for_farm_spawn = [c for c in components if mapping.get(c) != "cave"]
        max_farm_spawns = min(wheat // 10, len(candidates_for_farm_spawn) // 2)

        idx = 0
        for _ in range(max_farm_spawns):
            a = candidates_for_farm_spawn[idx]
            b = candidates_for_farm_spawn[idx + 1]
            mapping[a] = "spawn farmer"
            mapping[b] = "spawn farmer"
            idx += 2

        wheat_after_farm_spawns = wheat - max_farm_spawns * 10
        if wheat_after_farm_spawns < 0:
            wheat_after_farm_spawns = 0

        # 2b. Spawn Warriors: use remaining village villagers (not in cave or spawn farmer)
        candidates_for_warrior_spawn = [c for c in components if mapping.get(c) not in ("spawn farmer", "cave")]
        max_warrior_spawns = min(wheat_after_farm_spawns // 12, len(candidates_for_warrior_spawn) // 2)

        idx = 0
        for _ in range(max_warrior_spawns):
            a = candidates_for_warrior_spawn[idx]
            b = candidates_for_warrior_spawn[idx + 1]
            mapping[a] = "spawn warrior"
            mapping[b] = "spawn warrior"
            idx += 2

        # Step 3: Fallback for any remaining unassigned villagers
        for c in components:
            if c not in mapping:
                mapping[c] = "farm"

        # Apply the group assignments
        for component, gid in mapping.items():
            environment.assign_group(component, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - Warriors attack
        # - Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")