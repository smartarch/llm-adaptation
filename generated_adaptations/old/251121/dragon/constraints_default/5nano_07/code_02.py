from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning for Farmers
        # Wheat available for planning (read-only in env, but we can base decisions on current value)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Number of Farmers we can allocate to spawn farmer group
        k_f = min(len(farmers) // 2, int(wheat // 10))

        spawn_farmer_group = farmers[:2 * k_f]
        remaining_farmers_after_farmers_spawns = farmers[2 * k_f:]

        # Wheat after allocating for farmer spawns (we simulate consumption for planning)
        wheat_after_farm_spawns = max(0, wheat - 10 * k_f)

        # Number of Farmers we can allocate to spawn warrior group (to spawn new Warriors)
        k_w = min(len(remaining_farmers_after_farmers_spawns) // 2, int(wheat_after_farm_spawns // 12))

        spawn_warrior_group = remaining_farmers_after_farmers_spawns[:2 * k_w]
        remaining_farmers_for_farm = remaining_farmers_after_farmers_spawns[2 * k_w:]

        # 3) Assign groups to villagers
        for c in spawn_farmer_group:
            environment.assign_group(c, "spawn farmer")

        for c in spawn_warrior_group:
            environment.assign_group(c, "spawn warrior")

        for c in remaining_farmers_for_farm:
            environment.assign_group(c, "farm")

        # If there are any farmers we didn't categorize (edge cases), send them to farm as a default
        # (This is a safety net; should not typically trigger.)
        for c in []:
            environment.assign_group(c, "farm")

        # Note: Any villagers not in the Farmer/Warrior lists are assumed to be already handled
        # (e.g., new spawns will appear in subsequent steps). We keep the current logic focused on the
        # described groups.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the cave by role
        cave_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Warriors should attack the Dragon
        for w in cave_warriors:
            environment.assign_group(w, "attack")

        # 2) Farmers (if any) should go back to the Village
        cave_farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        for f in cave_farmers:
            environment.assign_group(f, "village")

        # If there were any other types (edge cases), send them to village as a safe default
        # (not strictly required by the problem, but ensures consistency)
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "village")