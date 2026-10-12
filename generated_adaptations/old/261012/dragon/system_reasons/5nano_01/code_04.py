from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Strategy: move all warriors to the cave to prepare for attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning plan based on available wheat and farmers
        wheat = getattr(environment.farm, "wheat", 0)

        spawns_farm = 0  # number of batches of farmers to spawn (each batch = 2 farmers)
        spawns_war = 0   # number of batches of warriors to spawn (each batch = 2 warriors)

        # Calculate how many farmer batches we can spawn
        max_farm_batches_by_wheat = wheat // 10
        max_farm_batches_by_farmers = len(farmers) // 2
        spawns_farm = min(2, max_farm_batches_by_wheat, max_farm_batches_by_farmers)

        wheat_after_farm = wheat - spawns_farm * 10
        remaining_farmers_after_farm = len(farmers) - spawns_farm * 2

        # Calculate how many warrior batches we can spawn with remaining resources
        max_war_batches_by_wheat = wheat_after_farm // 12
        max_war_batches_by_farmers = remaining_farmers_after_farm // 2
        spawns_war = min(2, max_war_batches_by_wheat, max_war_batches_by_farmers)

        # Assign groups for farmers destined to spawn
        idx = 0
        for _ in range(spawns_farm * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign groups for farmers destined to spawn war group
        for _ in range(spawns_war * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farming (stay in village)
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave:
        # - Warriors attack the Dragon
        # - Farmers return to the Village (stay in village by default)
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")