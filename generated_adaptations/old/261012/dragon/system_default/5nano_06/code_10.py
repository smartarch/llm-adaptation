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

        # Default: no movement yet
        to_cave = 0
        if group_cave and len(warriors) > 0:
            to_cave = 1  # conservative early attack

        # Move a small number of Warriors to the Cave
        if group_cave:
            for w in warriors[:to_cave]:
                environment.assign_group(w, group_cave)

        # Remaining warriors (not sent to cave yet)
        rest_warriors = warriors[to_cave:] if group_cave else warriors

        # If there are no farmers, just try to place remaining warriors into a valid group
        if not farmers:
            if group_farm:
                for w in rest_warriors:
                    environment.assign_group(w, group_farm)
            return

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)
        n_f = len(farmers)

        # Keep at least a small farming population to sustain wheat production
        min_in_village = 3
        max_farmer_spawns = max(0, (n_f - min_in_village) // 2)
        s_farmer = min(max_farmer_spawns, wheat // 10)

        idx = 0
        if group_spawn_farmer and s_farmer > 0:
            for _ in range(2 * s_farmer):
                if idx >= n_f:
                    break
                environment.assign_group(farmers[idx], group_spawn_farmer)
                idx += 1

        remaining = farmers[idx:]
        wheat_after_farmer = wheat - 10 * s_farmer

        # Decide warrior spawns from remaining farmers
        max_warrior_spawns = max(0, (len(remaining) - min_in_village) // 2)
        s_warrior = 0
        if group_spawn_warrior and wheat_after_farmer > 0:
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

        # Any remaining rest_warriors (not used yet) go to farming if possible
        for w in rest_warriors:
            if group_farm:
                environment.assign_group(w, group_farm)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Resolve group IDs (handle missing groups gracefully)
        group_attack = "attack" if "attack" in group_ids else None
        group_cave = "cave" if "cave" in group_ids else None
        group_village = "village" if "village" in group_ids else None

        Warriors = [c for c in components if c.role == "Warrior"]
        Farmers = [c for c in components if c.role == "Farmer"]

        # Gradual aggression: early steps use a conservative attack
        if group_attack and step < 4:
            if len(Warriors) > 0:
                environment.assign_group(Warriors[0], group_attack)
                for w in Warriors[1:]:
                    if group_village:
                        environment.assign_group(w, group_village)
                    elif group_cave:
                        environment.assign_group(w, group_cave)
            # If no Warriors, nothing to do
        else:
            if group_attack:
                for w in Warriors:
                    environment.assign_group(w, group_attack)

        for f in Farmers:
            if group_village:
                environment.assign_group(f, group_village)
            elif group_cave:
                environment.assign_group(f, group_cave)