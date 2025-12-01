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
        total_farmers = len(farmers)

        # Strategy: spawn farmers first, but keep at least 2 farmers in village for farming
        # Max number of farmer-spawns we can attempt without dropping below 2 farmers
        max_possible_farmer_spawns = max(0, (total_farmers - 2) // 2)
        s_farmer = min(max_possible_farmer_spawns, wheat // 10)

        # Assign 2*s_farmer farmers to the "spawn farmer" group
        idx = 0
        if group_spawn_farmer and s_farmer > 0:
            for i in range(2 * s_farmer):
                if idx >= total_farmers:
                    break
                environment.assign_group(farmers[idx], group_spawn_farmer)
                idx += 1

        # Remaining farmers after reserving for farmer spawns
        remaining = farmers[idx:]

        wheat_after_farmer = wheat - 10 * s_farmer

        # Now consider spawning Warriors from the remaining farmers
        # We want to keep at least 2 farmers in village after warrior spawns
        max_possible_warrior_spawns = max(0, (len(remaining) - 2) // 2)
        s_warrior = 0
        if group_spawn_warrior and wheat_after_farmer > 0:
            s_warrior = min(max_possible_warrior_spawns, wheat_after_farmer // 12)

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