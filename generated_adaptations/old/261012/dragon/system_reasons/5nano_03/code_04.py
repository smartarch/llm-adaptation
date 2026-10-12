from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Identify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all existing Warriors to the Cave for early DPS
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Decide spawning allocations for Farmers
        # Wheat available in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # How many farmer-spawns can we support? (2 farmers per spawn, 10 wheat per spawn)
        max_spawn_farm = 0
        if len(farmers) >= 2 and wheat >= 10:
            max_spawn_farm = min(len(farmers) // 2, wheat // 10)

        # After farmer-spawns, remaining farmers that can be allocated elsewhere
        remaining_farmers_after_farm_spawns = len(farmers) - 2 * max_spawn_farm
        wheat_after_farm_spawns = wheat - max_spawn_farm * 10

        # How many warrior-spawns can we support? (2 farmers per spawn, 12 wheat per spawn)
        max_spawn_warrior = 0
        if remaining_farmers_after_farm_spawns >= 2 and wheat_after_farm_spawns >= 12:
            max_spawn_warrior = min( remaining_farmers_after_farm_spawns // 2,
                                     wheat_after_farm_spawns // 12 )

        # 3) Assign groups for Farmers
        # First 2*max_spawn_farm farmers -> 'spawn farmer'
        # Next 2*max_spawn_warrior farmers -> 'spawn warrior'
        # Rest -> 'farm'
        for idx, f in enumerate(farmers):
            if idx < 2 * max_spawn_farm:
                environment.assign_group(f, "spawn farmer")
            elif idx < 2 * max_spawn_farm + 2 * max_spawn_warrior:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Warriors were already sent to the cave above; no further action needed here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: attack with Warriors; Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")