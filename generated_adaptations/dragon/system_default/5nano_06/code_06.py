from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Resolve group IDs (handle missing groups gracefully)
        group_farm = "farm" if "farm" in group_ids else None
        group_cave = "cave" if "cave" in group_ids else None
        group_spawn_farmer = "spawn farmer" if "spawn farmer" in group_ids else None
        group_spawn_warrior = "spawn warrior" if "spawn warrior" in group_ids else None

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Move all Warriors to the Cave (to fight)
        if group_cave:
            for w in warriors:
                environment.assign_group(w, group_cave)

        # If there are no farmers, nothing to spawn; just farm with any remaining
        if not farmers:
            return

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)
        n_f = len(farmers)

        # Step-based spawning strategy
        # Ensure at least 2 farmers remain in village to sustain wheat production
        def safe(n): return max(0, n)

        if step < 4:
            # Aggressive farmer spawning first (early growth)
            max_farmer_spawns = max(0, (n_f - 2) // 2)
            s_farmer = min(max_farmer_spawns, wheat // 10)
        else:
            # Later steps: balance growth and early offense
            max_farmer_spawns = max(0, (n_f - 2) // 2)
            s_farmer = min(max_farmer_spawns, wheat // 10)

        idx = 0
        if group_spawn_farmer and s_farmer > 0:
            for i in range(2 * s_farmer):
                if idx >= n_f:
                    break
                environment.assign_group(farmers[idx], group_spawn_farmer)
                idx += 1

        remaining = farmers[idx:]
        wheat_after_farmer = wheat - 10 * s_farmer

        # Now decide warrior spawns
        s_warrior = 0
        if group_spawn_warrior and wheat_after_farmer > 0:
            # Keep at least 2 farmers in village after spawns
            max_warrior_spawns = max(0, (len(remaining) - 2) // 2)
            s_warrior = min(max_warrior_spawns, wheat_after_farmer // 12)

        if group_spawn_warrior and s_warrior > 0:
            for i in range(2 * s_warrior):
                if i >= len(remaining):
                    break
                environment.assign_group(remaining[i], group_spawn_warrior)

        # Farmers left after spawns go to farming
        start_farm = 2 * s_warrior
        for c in remaining[start_farm:]:
            if group_farm:
                environment.assign_group(c, group_farm)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Resolve group IDs (handle missing groups gracefully)
        group_attack = "attack" if "attack" in group_ids else None
        group_cave = "cave" if "cave" in group_ids else None
        group_village = "village" if "village" in group_ids else None

        for c in components:
            if c.role == "Warrior":
                # Warriors should attack the Dragon
                if group_attack:
                    environment.assign_group(c, group_attack)
                elif group_cave:
                    environment.assign_group(c, group_cave)
            elif c.role == "Farmer":
                # Farmers should go to the Village
                if group_village:
                    environment.assign_group(c, group_village)
                elif group_cave:
                    environment.assign_group(c, group_cave)
            else:
                # Fallback: keep in cave if possible
                if group_cave:
                    environment.assign_group(c, group_cave)