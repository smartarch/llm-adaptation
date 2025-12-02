from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Start with clear assignments
        for c in components:
            # Default to farm for farmers or cave for warriors (will override below)
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # Warriors should go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawn strategy for Farmers
        wheat = getattr(environment.farm, "wheat", 0)
        total_farmers = len(farmers)

        # We'll spawn farmers first as long as we have two villagers per spawn and 10 wheat per spawn
        max_farm_spawns = min(total_farmers // 2, wheat // 10 if wheat >= 10 else 0)
        spawn_farmers_count = max_farm_spawns * 2  # number of farmers to assign to spawn_farm

        # Assign the first chunk to spawn farmer
        assigned_to_spawn_farm = 0
        for idx in range(min(spawn_farmers_count, total_farmers)):
            c = farmers[idx]
            environment.assign_group(c, "spawn farmer")
            assigned_to_spawn_farm += 1

        # Remaining farmers after assigning to spawn farmer
        remaining_farmers_after_farm_spawn = total_farmers - assigned_to_spawn_farm

        # Wheat left after potential farmer spawns (approximate)
        wheat_after_farm_spawns = wheat - (max_farm_spawns * 10)

        # Spawn warriors using remaining farmers if possible
        max_war_spawns = 0
        if wheat_after_farm_spawns >= 12 and remaining_farmers_after_farm_spawn >= 2:
            max_war_spawns = min(remaining_farmers_after_farm_spawn // 2, wheat_after_farm_spawns // 12)

        spawn_warriors_count = max_war_spawns * 2
        start_war_spawn_idx = assigned_to_spawn_farm
        for idx in range(start_war_spawn_idx, min(start_war_spawn_idx + spawn_warriors_count, total_farmers)):
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")

        # Remaining farmers (not used for spawning in this step) go to farming
        for idx in range(assigned_to_spawn_farm + spawn_warriors_count, total_farmers):
            c = farmers[idx]
            environment.assign_group(c, "farm")

        # Note: Any farmers not in the farmers list were Warriors or already handled.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack, Farmers go back to village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should go to the village
                environment.assign_group(c, "village")