from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Strategy in Village:
        - Spawn Farmers as much as possible using Wheat and pairs of Farmers.
        - Then spawn Warriors using remaining Wheat and Farmer pairs.
        - Remaining Farmers stay in Village to farm.
        - All Warriors should move to the Cave (to be in Cave and fight later).
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current Wheat in Farm (default to 0 if farm not present)
        W = 0
        farm = getattr(environment, "farm", None)
        if farm is not None:
            W = getattr(farm, "wheat", 0)

        # Spawn as many Farmers as possible: need 2 farmers per spawn, 10 wheat per spawn
        max_spawn_farmers = len(farmers) // 2
        p_farm = min(max_spawn_farmers, W // 10)

        # Wheat remaining after spawning farmers
        W_remaining = W - p_farm * 10

        # Remaining farmers after allocating for farmer spawns
        remaining_farmers_after_farm_spawns = len(farmers) - 2 * p_farm

        # Spawn as many Warriors as possible with remaining wheat: need 2 farmers per spawn, 12 wheat per spawn
        p_war = min(remaining_farmers_after_farm_spawns // 2, W_remaining // 12)

        # Define groups for this step
        spawn_farmers = farmers[:2 * p_farm]
        spawn_warriors = farmers[2 * p_farm: 2 * p_farm + 2 * p_war]
        farmers_to_farm = farmers[2 * p_farm + 2 * p_war :]

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in farmers_to_farm:
            environment.assign_group(c, "farm")

        # Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Strategy in Cave:
        - All Warriors -> "attack" (attack the Dragon)
        - All Farmers -> "village" (return to Village to farm/spawn)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")