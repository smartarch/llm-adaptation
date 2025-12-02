from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in the village by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to cave (to travel there)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning for Farmers
        # Wheat available in the farm
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0  # If farm object isn't available for some reason

        n_farmers = len(farmers)

        # Determine how many Warrior spawns we can perform this step
        max_warrior_spawns = min(n_farmers // 2, wheat // 12)

        # Remaining farmers after allocating for Warrior spawns
        remaining_farmers = n_farmers - 2 * max_warrior_spawns

        # Determine how many Farmer spawns we can perform with remaining wheat
        max_farmer_spawns = min(remaining_farmers // 2, (wheat - 12 * max_warrior_spawns) // 10)

        # Allocate farmers to groups
        idx = 0
        # Farmers chosen for Warrior spawns
        warrior_spawn_villagers = farmers[idx: idx + 2 * max_warrior_spawns]
        idx += 2 * max_warrior_spawns

        # Farmers chosen for Farmer spawns
        farmer_spawn_villagers = farmers[idx: idx + 2 * max_farmer_spawns]
        idx += 2 * max_farmer_spawns

        # Remaining farmers will farm
        farming_farmers = farmers[idx:]

        for f in warrior_spawn_villagers:
            environment.assign_group(f, "spawn warrior")

        for f in farmer_spawn_villagers:
            environment.assign_group(f, "spawn farmer")

        for f in farming_farmers:
            environment.assign_group(f, "farm")

        # If there are any farmers not in the village after above (shouldn't happen), send them to farm by default
        # (Not strictly necessary since we assigned all farmers above)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, make all Warriors attack; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to Village
                environment.assign_group(c, "village")