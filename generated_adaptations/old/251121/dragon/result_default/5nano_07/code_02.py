from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All warriors go to the cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village
        if not farmers:
            return

        total_farmers = len(farmers)
        # Ensure at least one farmer remains to farm
        farm_count = max(1, total_farmers - 1)
        farmers_to_farm = farmers[:farm_count]
        remaining = farmers[farm_count:]

        # Current wheat in the Farm
        wheat = environment.farm.wheat

        # Spawning plan (simple heuristic)
        spawn_farmer_count = 0
        spawn_warrior_count = 0

        # If at least 2 farmers available in the remaining pool and enough wheat, spawn a farmer
        if len(remaining) >= 2 and wheat >= 10:
            spawn_farmer_count = 1  # uses 2 villagers

        # If enough villagers remain after allocating to spawn farmer, and enough wheat, spawn a warrior
        if len(remaining) - spawn_farmer_count*2 >= 2 and wheat >= 12:
            spawn_warrior_count = 1  # uses 2 more villagers

        # Assign farmers
        for f in farmers_to_farm:
            environment.assign_group(f, "farm")

        # Assign spawn farmer group (2 villagers per spawn)
        idx = 0
        for _ in range(spawn_farmer_count * 2):
            if idx < len(remaining):
                environment.assign_group(remaining[idx], "spawn farmer")
                idx += 1

        # Assign spawn warrior group (2 villagers per spawn)
        for _ in range(spawn_warrior_count * 2):
            if idx < len(remaining):
                environment.assign_group(remaining[idx], "spawn warrior")
                idx += 1

        # Any leftover remaining farmers go to farm
        for j in range(idx, len(remaining)):
            environment.assign_group(remaining[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # All Warriors should attack; all Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # If there's any other type (unexpected), default to staying in cave
                environment.assign_group(c, "cave")