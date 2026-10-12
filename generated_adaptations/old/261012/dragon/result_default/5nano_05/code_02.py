from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current farm wheat
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Spawn planning: first Farmer-spawns (2 farmers + 10 wheat per spawn)
        spawn_farmer_slots = min(len(farmers) // 2, int(wheat // 10))
        spawn_farmer_count_paired = spawn_farmer_slots * 2
        wheat_after_farmer_spawns = wheat - spawn_farmer_slots * 10

        # Then Warrior-spawns (2 farmers + 12 wheat per spawn) with remaining farmers
        remaining_farmers_for_warrior = len(farmers) - spawn_farmer_count_paired
        spawn_warrior_slots = min(remaining_farmers_for_warrior // 2, int(wheat_after_farmer_spawns // 12))
        spawn_warrior_count_paired = spawn_warrior_slots * 2

        # Farmers left to farm
        farmers_in_farm_group = len(farmers) - spawn_farmer_count_paired - spawn_warrior_count_paired

        # Assign Farmers to their groups
        i = 0
        for f in farmers:
            if i < spawn_farmer_count_paired:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count_paired + spawn_warrior_count_paired:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")
            i += 1

        # Assign Warriors to cave (they will head to Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack, Farmers should go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")