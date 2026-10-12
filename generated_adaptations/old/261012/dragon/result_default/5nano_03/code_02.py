from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Warriors should go to the Cave (to be handled in cave step as attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers strategy: farm vs. spawn
        wheat = 0
        try:
            wheat = int(environment.farm.wheat)
        except Exception:
            # If wheat information isn't available for some reason, default to 0
            wheat = 0

        n_farmers = len(farmers)
        # If no farmers, nothing to spawn or farm
        if n_farmers == 0:
            return

        # Compute possible spawns
        # First, max spawns for farmers
        max_farm_spawns = min(n_farmers // 2, wheat // 10)

        # Wheat remaining after farming spawns
        wheat_after_farm_spawns = wheat - max_farm_spawns * 10

        # Remaining farmers after allocating to farm spawns
        remaining_farmers = n_farmers - max_farm_spawns * 2

        # Now compute possible spawns for warriors with remaining wheat
        max_war_spawns = min(remaining_farmers // 2, wheat_after_farm_spawns // 12)

        # Assign first 2*max_farm_spawns farmers to "spawn farmer"
        idx = 0
        for _ in range(max_farm_spawns * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign next 2*max_war_spawns farmers to "spawn warrior"
        for _ in range(max_war_spawns * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farm
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # Note: If some farmers were not assigned due to edge cases, they default to "farm"
        # However, the above loop covers all farmers.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors should attack Dragon; Farmers should go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go to Village to farm or spawn
                environment.assign_group(c, "village")