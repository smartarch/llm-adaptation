from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the farm
        try:
            available_wheat = int(getattr(environment.farm, "wheat", 0))
        except Exception:
            available_wheat = 0

        num_farmers = len(farmers)

        # Compute possible spawns
        # Spawn Warrior: 2 farmers + 12 wheat -> 1 Warrior
        max_war_spawns = min(num_farmers // 2, available_wheat // 12)

        # After reserving for warrior spawns, compute remaining wheat
        remaining_wheat_after_war = available_wheat - max_war_spawns * 12
        remaining_farmers_after_war = num_farmers - max_war_spawns * 2

        # Spawn Farmer: 2 farmers + 10 wheat -> 1 Farmer
        max_farm_spawns = min(remaining_farmers_after_war // 2, remaining_wheat_after_war // 10)

        # Assign groups
        # 1) Warriors go to cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers allocated to spawn warrior (2 per spawn)
        spawn_warrior_vills = farmers[0 : 2 * max_war_spawns]
        for f in spawn_warrior_vills:
            environment.assign_group(f, "spawn warrior")

        # 3) Farmers allocated to spawn farmer (2 per spawn)
        start_for_farm_spawns = 2 * max_war_spawns
        spawn_farmer_vills = farmers[start_for_farm_spawns : start_for_farm_spawns + 2 * max_farm_spawns]
        for f in spawn_farmer_vills:
            environment.assign_group(f, "spawn farmer")

        # 4) Remaining farmers go to farming in the village
        remaining_farmers = farmers[start_for_farm_spawns + 2 * max_farm_spawns :]
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        # Note: If there are no farmers, Warriors still go to cave; no spawns created this turn.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack the Dragon.
        # Farmers should stay in village (or go to village as needed). We assign accordingly.
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers stay in the Village
                environment.assign_group(c, "village")