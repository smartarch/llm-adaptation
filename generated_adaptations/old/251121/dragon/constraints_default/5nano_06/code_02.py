from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning strategy for Farmers
        # Current wheat available in the farm
        wheat_available = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat_available = int(environment.farm.wheat)

        # Number of Farmers that can be allocated to spawn Farmer: 2 per spawn, consuming 10 wheat per spawn
        k_farm = min(len(farmers) // 2, max(0, wheat_available // 10))

        spawn_farmers_list = farmers[:2 * k_farm]
        farm_candidates = farmers[2 * k_farm:]

        # Update wheat after farm spawns (approximate; environment will handle actual consumption)
        wheat_after_farm_spawns = wheat_available - 10 * k_farm

        # Number of Farmers that can be allocated to spawn Warrior: 2 per spawn, consuming 12 wheat per spawn
        k_war = min(len(farm_candidates) // 2, max(0, wheat_after_farm_spawns // 12))

        spawn_warrior_list = farm_candidates[:2 * k_war]
        remaining_farmers = farm_candidates[2 * k_war:]

        # Assign groups accordingly
        for c in spawn_farmers_list:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
        for c in spawn_warrior_list:
            environment.assign_group(c, "spawn warrior")

        # If there were no farmers, ensure we still assign any remaining warriors to cave and any farmers (none) to village
        # (Every component should be assigned exactly one group already)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack; Farmers should go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go to Village
                environment.assign_group(c, "village")
        # Note: The "cave" group can remain unused in this step; it's valid to have empty groups.