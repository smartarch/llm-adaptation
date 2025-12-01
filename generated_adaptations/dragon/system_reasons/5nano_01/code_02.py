from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Strategy:
        # - All Warriors move to the cave (to then attack)
        # - All Farmers stay in the village, but we may allocate some to spawning groups
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide spawning allocations based on available wheat and number of farmers
        wheat = getattr(environment.farm, "wheat", 0)

        # Heuristic spawning plan:
        # - Spawn up to 2 batches of farmers (cost 10 wheat each, 2 farmers per batch)
        # - Then, with remaining wheat, spawn at most 1 batch of warriors (cost 12 wheat, 2 farmers per batch)
        spawns_farm = 0  # number of batches for spawning farmers
        spawns_war = 0   # number of batches for spawning warriors

        max_farm_batches_by_wheat = wheat // 10
        max_farm_batches_by_farmers = len(farmers) // 2
        spawns_farm = min(2, max_farm_batches_by_wheat, max_farm_batches_by_farmers)

        wheat_after_farm = wheat - spawns_farm * 10
        remaining_farmers_after_farm = len(farmers) - spawns_farm * 2
        if remaining_farmers_after_farm >= 2 and wheat_after_farm >= 12:
            spawns_war = 1  # try to spawn one batch of warriors if possible

        # Assign groups for farmers
        # First, assign farmers destined for spawning to their groups
        idx = 0
        # Assign farmers to spawn farmer group (2 per batch)
        for _ in range(spawns_farm * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign farmers to spawn warrior group (2 per batch)
        for _ in range(spawns_war * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farming group (stay in village)
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Farmers already moved to cave above remain unaffected for now
        # If there were any other villagers (e.g., additional roles), ensure they default to farming
        # (This block is defensive; according to the task, only Farmers/Warrriors exist.)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave:
        # - Warriors should attack the Dragon
        # - Farmers should go back to the Village
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")