from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Get Wheat available in the Farm
        wheat = 0
        if hasattr(environment, "farm") and environment.farm is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave (to go attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning among Farmers
        # Determine how many spawns we can support with current wheat and available farmers
        max_spawn_farmers = min(len(farmers) // 2, wheat // 10 if wheat >= 10 else 0)

        # Wheat left after farmer spawns
        wheat_after_farm_spawns = max(0, wheat - max_spawn_farmers * 10)

        # Remaining farmers after allocating 2 per spawn for farmers
        remaining_farmers_after_farm_spawns = len(farmers) - 2 * max_spawn_farmers

        # Determine how many spawns we can support for warriors (needs 12 wheat per spawn)
        max_spawn_warriors = 0
        if wheat_after_farm_spawns >= 12 and remaining_farmers_after_farm_spawns >= 2:
            max_spawn_warriors = min( remaining_farmers_after_farm_spawns // 2,
                                      wheat_after_farm_spawns // 12 )

        spawn_farmer_count = int(max_spawn_farmers)
        spawn_warrior_count = int(max_spawn_warriors)

        # 3) Assign groups for Farmers
        # We'll assign:
        # - First 2*spawn_farmer_count farmers to "spawn farmer"
        # - Next 2*spawn_warrior_count farmers to "spawn warrior"
        # - The rest to "farm"
        total_farmers = len(farmers)
        used_for_farmers = 0

        # Assign to "spawn farmer"
        for i, c in enumerate(farmers):
            if i < 2 * spawn_farmer_count:
                environment.assign_group(c, "spawn farmer")
            elif i < 2 * spawn_farmer_count + 2 * spawn_warrior_count:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

        # 4) Farmers already assigned to "cave" are Warriors; no action needed for Farmers here

        # Note: Warriors are already moved to "cave" above. If there were any farmers left in cave by some edge case,
        # they'd be assigned to village below in assign_in_cave, but here we assume current village step had farmers in village.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, command Warriors to attack and Farmers back to Village
        for c in components:
            role = getattr(c, "role", None)

            if role == "Warrior":
                # Attack the Dragon
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Return Farmers to Village
                environment.assign_group(c, "village")
            else:
                # If an unexpected type appears, default to staying in Cave
                environment.assign_group(c, "cave")