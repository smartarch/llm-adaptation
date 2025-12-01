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

        # Strategy: move only a small number of Warriors to the Cave early to reduce initial casualties
        # and keep the rest in village to farm or wait for later deployment.
        if group_cave and len(warriors) > 0:
            to_cave = 1  # conservative early attack
            for i in range(min(to_cave, len(warriors))):
                environment.assign_group(warriors[i], group_cave)

        rest_warriors = warriors[to_cave:] if group_cave else warriors

        # If there are no farmers, nothing to spawn; just keep any remaining Warriors in village or cave as per below
        if not farmers:
            # If there are remaining warriors not sent to cave, assign them to farming if possible
            for w in rest_warriors:
                if group_farm:
                    environment.assign_group(w, group_farm)
            return

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)
        n_f = len(farmers)

        # Keep at least 3 farmers in village to sustain wheat production
        min_in_village = 3
        max_farmer_spawns = max(0, (n_f - min_in_village) // 2)
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

        # Any remaining Warriors (not assigned to cave yet) can go to farming as a fallback
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

        # Gradual aggression: in early steps, send only 1 Warrior to attack to reduce casualties
        if group_attack and step < 4:
            if len(Warriors) > 0:
                environment.assign_group(Warriors[0], group_attack)
                # Move any additional Warriors back toward village if possible
                for w in Warriors[1:]:
                    if group_village:
                        environment.assign_group(w, group_village)
                    elif group_cave:
                        environment.assign_group(w, group_cave)
            else:
                # No warriors to attack; do nothing
                pass
        else:
            # Later steps: send all Warriors to attack
            for w in Warriors:
                environment.assign_group(w, group_attack)

        # Farmers go to village (or cave as fallback)
        for f in Farmers:
            if group_village:
                environment.assign_group(f, group_village)
            elif group_cave:
                environment.assign_group(f, group_cave)