from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Define available group IDs (safely handle missing ones)
        group_farm = "farm" if "farm" in group_ids else None
        group_cave = "cave" if "cave" in group_ids else None
        group_spawn_farmer = "spawn farmer" if "spawn farmer" in group_ids else None
        group_spawn_warrior = "spawn warrior" if "spawn warrior" in group_ids else None

        # Separate villagers by role
        farmers = []
        warriors_in_village = []
        for c in components:
            # Warriors should travel to the Cave
            if c.role == "Warrior":
                if group_cave:
                    environment.assign_group(c, group_cave)
                else:
                    # Fallback: assign to farm if no cave group present
                    if group_farm:
                        environment.assign_group(c, group_farm)
            elif c.role == "Farmer":
                farmers.append(c)
            else:
                # Unknown role; assign to farm as a safe default if possible
                if group_farm:
                    environment.assign_group(c, group_farm)

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        n_farmers = len(farmers)

        # Determine how many new Farmers we can spawn
        s_farmer = min(n_farmers // 2, wheat // 10)

        # Assign 2*s_farmer farmers to spawn farmer group
        idx = 0
        if group_spawn_farmer and s_farmer > 0:
            for i in range(2 * s_farmer):
                if i >= len(farmers):
                    break
                environment.assign_group(farmers[i], group_spawn_farmer)
            idx = min(2 * s_farmer, len(farmers))

        # Remaining farmers after reserving for farmer spawns
        remaining = farmers[idx:]

        # Wheat left after farmer spawns
        wheat_after_farmer = wheat - 10 * s_farmer

        # Determine how many new Warriors we can spawn from remaining farmers
        s_warrior = 0
        if group_spawn_warrior and wheat_after_farmer > 0:
            s_warrior = min(len(remaining) // 2, wheat_after_farmer // 12)

        if group_spawn_warrior and s_warrior > 0:
            for i in range(2 * s_warrior):
                if i >= len(remaining):
                    break
                environment.assign_group(remaining[i], group_spawn_warrior)

        # Farmers that are not used for spawning go to farming
        start_farm = 2 * s_warrior
        for c in remaining[start_farm:]:
            if group_farm:
                environment.assign_group(c, group_farm)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Define available group IDs (safely handle missing ones)
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
                # Fallback: try to keep them in cave if possible
                if group_cave:
                    environment.assign_group(c, group_cave)